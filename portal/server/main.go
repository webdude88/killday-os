// killday-serve runs The Kill-Day Almanac on every platform. It serves the
// portal and library files with byte-range support, supervises kiwix-serve,
// and adds safety banners to encyclopedia pages as they pass through it.
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"html"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"
)

type item struct {
	ID         string `json:"id"`
	Title      string `json:"title"`
	Kind       string `json:"kind"`
	Path       string `json:"path"`
	Disclaimer string `json:"disclaimer"`
}

type module struct {
	ID         string `json:"id"`
	Disclaimer string `json:"disclaimer"`
	Items      []item `json:"items"`
}

type catalog struct {
	Disclaimers map[string]string `json:"disclaimers"`
	Modules     []module          `json:"modules"`
}

type server struct {
	portal    string
	library   string
	cat       catalog
	kiwixAddr string
}

var bodyTag = regexp.MustCompile(`(?i)<body[^>]*>`)
var allowedLibraryRoots = map[string]bool{"docs": true, "maps": true, "books": true}

func loadCatalog(portal string) catalog {
	var cat catalog
	raw, err := os.ReadFile(filepath.Join(portal, "catalog.json"))
	if err != nil {
		log.Printf("no catalog: %v", err)
		return cat
	}
	if err := json.Unmarshal(raw, &cat); err != nil {
		log.Printf("bad catalog: %v", err)
	}
	return cat
}

// disclaimerFor maps a kiwix book name such as "mdwiki_en_all_maxi_2025-11" to
// its banner. It uses the longest matching catalog ID so specific entries win.
func (s *server) disclaimerFor(book string) string {
	best, kind := -1, ""
	for _, mod := range s.cat.Modules {
		for _, it := range mod.Items {
			if it.Kind != "zim" || !strings.HasPrefix(book, strings.TrimSuffix(filepath.Base(it.Path), ".zim")) && !strings.HasPrefix(book, it.ID) {
				continue
			}
			if len(it.ID) > best {
				best = len(it.ID)
				kind = it.Disclaimer
				if kind == "" {
					kind = mod.Disclaimer
				}
			}
		}
	}
	if kind == "" {
		kind = "general"
	}
	return s.cat.Disclaimers[kind]
}

func bannerHTML(text string) []byte {
	return []byte(`<div style="position:sticky;top:0;z-index:2147483647;background:#3a0d13;color:#fff;` +
		`border-bottom:3px solid #FF3B4E;font:600 16px/1.4 sans-serif;padding:10px 16px">` +
		html.EscapeString(text) + `</div>`)
}

func (s *server) kiwixProxy() http.Handler {
	target, _ := url.Parse("http://" + s.kiwixAddr)
	proxy := httputil.NewSingleHostReverseProxy(target)
	director := proxy.Director
	proxy.Director = func(r *http.Request) {
		director(r)
		r.Header.Del("Accept-Encoding") // HTML must arrive uncompressed so banners can be added.
	}
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		http.Error(w, "Corrupted? Still alive. The encyclopedia engine is not running.", http.StatusBadGateway)
	}
	proxy.ModifyResponse = func(resp *http.Response) error {
		const prefix = "/kiwix/content/"
		path := resp.Request.URL.Path
		if !strings.HasPrefix(path, prefix) || !strings.Contains(resp.Header.Get("Content-Type"), "text/html") {
			return nil
		}
		book := strings.SplitN(strings.TrimPrefix(path, prefix), "/", 2)[0]
		text := s.disclaimerFor(book)
		if text == "" {
			return nil
		}
		raw, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			return err
		}
		banner := bannerHTML(text)
		var out []byte
		if loc := bodyTag.FindIndex(raw); loc != nil {
			out = append(append(append([]byte{}, raw[:loc[1]]...), banner...), raw[loc[1]:]...)
		} else {
			out = append(banner, raw...)
		}
		resp.Body = io.NopCloser(bytes.NewReader(out))
		resp.ContentLength = int64(len(out))
		resp.Header.Set("Content-Length", strconv.Itoa(len(out)))
		return nil
	}
	return proxy
}

func (s *server) libraryFiles() http.Handler {
	files := http.FileServer(http.Dir(s.library))
	return http.StripPrefix("/library", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		parts := strings.SplitN(strings.TrimPrefix(r.URL.Path, "/"), "/", 2)
		if len(parts) < 2 || parts[1] == "" || strings.HasSuffix(r.URL.Path, "/") || !allowedLibraryRoots[parts[0]] {
			http.NotFound(w, r)
			return
		}
		files.ServeHTTP(w, r)
	}))
}

func persistenceUnlocked() bool {
	raw, err := os.ReadFile("/proc/mounts")
	if err != nil {
		return false
	}
	for _, line := range strings.Split(string(raw), "\n") {
		if strings.Contains(line, "/run/live/persistence") && strings.Contains(line, "/dev/mapper/") {
			return true
		}
	}
	return false
}

func (s *server) status(w http.ResponseWriter, r *http.Request) {
	installed := []string{}
	for _, mod := range s.cat.Modules {
		for _, it := range mod.Items {
			if _, err := os.Stat(filepath.Join(s.library, filepath.FromSlash(it.Path))); err == nil {
				installed = append(installed, it.ID)
			}
		}
	}
	maps, _ := filepath.Glob(filepath.Join(s.library, "maps", "*.pmtiles"))
	names := []string{}
	for _, m := range maps {
		names = append(names, filepath.Base(m))
	}
	sort.Strings(names)
	conn, err := http.Get("http://" + s.kiwixAddr + "/kiwix/")
	kiwixUp := err == nil
	if conn != nil {
		conn.Body.Close()
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"installed":   installed,
		"maps":        names,
		"kiwix":       kiwixUp,
		"persistence": persistenceUnlocked(),
		"platform":    runtime.GOOS,
	})
}

func toolPath(library, name string) string {
	if runtime.GOOS == "windows" {
		name += ".exe"
	}
	candidates := []string{filepath.Join(library, "tools", runtime.GOOS+"-"+runtime.GOARCH, name)}
	if runtime.GOOS == "darwin" && runtime.GOARCH == "arm64" {
		candidates = append(candidates, filepath.Join(library, "tools", "darwin-amd64", name))
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}
	if found, err := exec.LookPath(name); err == nil {
		return found
	}
	return ""
}

// superviseKiwix restarts kiwix-serve if it exits, so one bad page cannot take
// the encyclopedias down for the rest of the session.
func (s *server) superviseKiwix(port string) {
	zims, _ := filepath.Glob(filepath.Join(s.library, "zim", "*.zim"))
	bin := toolPath(s.library, "kiwix-serve")
	if len(zims) == 0 || bin == "" {
		log.Printf("kiwix-serve not started (zims=%d, binary=%q)", len(zims), bin)
		return
	}
	args := append([]string{"--address=127.0.0.1", "--port=" + port, "--urlRootLocation=/kiwix", "--nolibrarybutton"}, zims...)
	for {
		cmd := exec.Command(bin, args...)
		cmd.Stdout, cmd.Stderr = os.Stdout, os.Stderr
		log.Printf("starting kiwix-serve with %d archive(s)", len(zims))
		if err := cmd.Run(); err != nil {
			log.Printf("kiwix-serve exited: %v", err)
		}
		time.Sleep(3 * time.Second)
	}
}

func openBrowser(target string) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", target)
	case "darwin":
		cmd = exec.Command("open", target)
	default:
		cmd = exec.Command("xdg-open", target)
	}
	if err := cmd.Start(); err != nil {
		log.Printf("could not open a browser, visit %s manually: %v", target, err)
	}
}

func main() {
	library := flag.String("library", ".", "root of the KILLDAY_LIB content")
	portal := flag.String("portal", "", "portal directory (default: <library>/almanac)")
	addr := flag.String("addr", "127.0.0.1", "address to listen on")
	port := flag.Int("port", 8642, "portal port")
	kiwixPort := flag.Int("kiwix-port", 8643, "kiwix-serve port")
	openIt := flag.Bool("open", false, "open the portal in the default browser")
	flag.Parse()

	root, err := filepath.Abs(*library)
	if err != nil {
		log.Fatal(err)
	}
	dir := *portal
	if dir == "" {
		dir = filepath.Join(root, "almanac")
	}
	s := &server{portal: dir, library: root, cat: loadCatalog(dir), kiwixAddr: fmt.Sprintf("127.0.0.1:%d", *kiwixPort)}
	go s.superviseKiwix(strconv.Itoa(*kiwixPort))

	mux := http.NewServeMux()
	mux.Handle("/kiwix/", s.kiwixProxy())
	mux.Handle("/library/", s.libraryFiles())
	mux.HandleFunc("/api/status", s.status)
	mux.Handle("/", http.FileServer(http.Dir(dir)))

	listen := fmt.Sprintf("%s:%d", *addr, *port)
	log.Printf("The Kill-Day Almanac is on http://%s/", listen)
	if *openIt {
		go func() {
			time.Sleep(time.Second)
			openBrowser(fmt.Sprintf("http://127.0.0.1:%d/", *port))
		}()
	}
	log.Fatal(http.ListenAndServe(listen, mux))
}
