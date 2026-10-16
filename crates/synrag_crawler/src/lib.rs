use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::LazyLock;
use std::time::SystemTime;

use ignore::WalkBuilder;
use pyo3::prelude::*;
use rayon::prelude::*;
use regex::Regex;

// Directorios y patrones ignorados
static IGNORE_DIRS: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    let mut s = HashSet::new();
    for dir in &[
        "node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build",
        ".cache", ".next", ".turbo", "target", "obj", ".idea", ".vscode",
        "coverage", ".steam", "asmp-release", "proteus_extracted",
        "dataset-universidades", "Modulegit", "Codex", "playwright-report",
        "test-results", "android", "ios", "pnpm-store", "storybook-static",
        "appwrite-dist",
    ] {
        s.insert(*dir);
    }
    s
});

static IGNORE_DIR_SUBSTR: &[&str] = &[".git-backup", "-backup-", ".bak", "-dist"];

static IGNORE_FILES: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    let mut s = HashSet::new();
    for f in &[
        "pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lock",
        "composer.lock", "Cargo.lock", "poetry.lock",
    ] {
        s.insert(*f);
    }
    s
});

static ALLOWED_EXTENSIONS: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    let mut s = HashSet::new();
    for ext in &[
        ".py", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx", ".lua", ".sh", ".bash",
        ".zsh", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".html", ".css",
        ".scss", ".conf", ".sql", ".qml", ".desktop", ".rst", ".mdx", ".adoc",
    ] {
        s.insert(*ext);
    }
    s
});

static RE_ARCHIVO_SENSIBLE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)(credential|secret|service[-_]?account|adminsdk|google-services|\.pem$|\.key$|id_rsa|keystore|\.p12$|\.env)").unwrap()
});

static RE_PEM: LazyLock<Regex> = LazyLock::new(|| {
    // Solo una llave de verdad (cabecera + cuerpo base64): mencionar la cabecera no borra el resto.
    Regex::new(r"-----BEGIN [A-Z ]*PRIVATE KEY-----\s*(?:[A-Za-z0-9+/=]{16,}\s*)+(?:-----END [A-Z ]*PRIVATE KEY-----)?").unwrap()
});

static RE_TOKENS: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\b(?:sk-[A-Za-z0-9_\-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|xox[bpoas]-[A-Za-z0-9\-]{20,}|AIza[0-9A-Za-z_\-]{30,}|AKIA[0-9A-Z]{16}|standard_[a-f0-9]{40,}|re_[A-Za-z0-9]{20,}|AQ\.[A-Za-z0-9_\-]{40,})\b").unwrap()
});

static RE_ASIGNACION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?i)((?:api[_-]?key|secret|passw(?:or)?d|token|private[_-]?key|client[_-]?secret)[A-Za-z0-9_]*["']?\s*[:=]\s*["']?)([A-Za-z0-9_\-\./+=]{16,})"#).unwrap()
});

const OCULTO: &str = "[SECRETO-OCULTO]";

/// Enmascara secretos en el texto y devuelve si se modifico el contenido
#[pyfunction]
pub fn mask_secrets(texto: &str) -> (String, bool) {
    let mut modificado = false;
    let mut resultado = texto.to_string();

    if RE_PEM.is_match(&resultado) {
        resultado = RE_PEM.replace_all(&resultado, OCULTO).to_string();
        modificado = true;
    }
    if RE_TOKENS.is_match(&resultado) {
        resultado = RE_TOKENS.replace_all(&resultado, OCULTO).to_string();
        modificado = true;
    }
    if RE_ASIGNACION.is_match(&resultado) {
        resultado = RE_ASIGNACION.replace_all(&resultado, "${1}[SECRETO-OCULTO]").to_string();
        modificado = true;
    }

    (resultado, modificado)
}

/// Comprueba si un nombre de archivo corresponde a credenciales o secretos
#[pyfunction]
pub fn is_sensitive_file(filename: &str) -> bool {
    RE_ARCHIVO_SENSIBLE.is_match(filename)
}

/// Representa un archivo indexado listo para procesamiento AST o ingesta
#[pyclass(get_all)]
#[derive(Clone, Debug)]
pub struct ScannedFile {
    pub path: String,
    pub rel_path: String,
    pub rel_base: String,
    pub project: String,
    pub filename: String,
    pub extension: String,
    pub content: String,
    pub mtime: f64,
    pub size: usize,
    pub secrets_masked: bool,
}

#[pymethods]
impl ScannedFile {
    fn __repr__(&self) -> String {
        format!(
            "<ScannedFile rel='{}' project='{}' size={} masked={}>",
            self.rel_path, self.project, self.size, self.secrets_masked
        )
    }
}

/// Representa metadatos ligeros de un archivo sin cargar su contenido
#[pyclass(get_all)]
#[derive(Clone, Debug)]
pub struct ScannedFileMetadata {
    pub path: String,
    pub rel_path: String,
    pub rel_base: String,
    pub project: String,
    pub filename: String,
    pub extension: String,
    pub mtime: f64,
    pub size: usize,
}

#[pymethods]
impl ScannedFileMetadata {
    fn __repr__(&self) -> String {
        format!(
            "<ScannedFileMetadata rel='{}' project='{}' size={}>",
            self.rel_path, self.project, self.size
        )
    }
}

/// Comprueba si un archivo debe ser indexado segun las reglas de exclusion
#[pyfunction]
pub fn should_index(file_path_str: &str, base_dir_str: &str) -> bool {
    let file_path = Path::new(file_path_str);
    let base_dir = Path::new(base_dir_str);

    let Ok(rel) = file_path.strip_prefix(base_dir) else {
        return false;
    };

    // Comprobar carpetas intermedias
    if let Some(parent) = rel.parent() {
        for comp in parent.components() {
            let part = comp.as_os_str().to_string_lossy();
            if IGNORE_DIRS.contains(part.as_ref()) || part.starts_with('.') {
                return false;
            }
            if IGNORE_DIR_SUBSTR.iter().any(|s| part.contains(s)) {
                return false;
            }
        }
    }

    let Some(filename) = file_path.file_name().and_then(|s| s.to_str()) else {
        return false;
    };

    if IGNORE_FILES.contains(filename) || RE_ARCHIVO_SENSIBLE.is_match(filename) {
        return false;
    }

    let ext = file_path
        .extension()
        .and_then(|s| s.to_str())
        .map(|s| format!(".{}", s.to_lowercase()))
        .unwrap_or_default();

    if !ALLOWED_EXTENSIONS.contains(ext.as_str()) {
        return false;
    }

    match fs::metadata(file_path) {
        Ok(m) => m.len() <= 250 * 1024,
        Err(_) => false,
    }
}

fn determine_project(rel_base: &Path, base_dir: &Path, fixed_project: Option<&str>) -> String {
    if let Some(fixed) = fixed_project {
        return fixed.to_string();
    }
    let mut components = rel_base.components();
    if let Some(first) = components.next() {
        let first_str = first.as_os_str().to_string_lossy();
        if components.next().is_some() {
            return first_str.to_string();
        }
    }
    base_dir
        .file_name()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_else(|| "default".to_string())
}

struct FileCandidate {
    path: PathBuf,
    base_dir: PathBuf,
    fixed_project: Option<String>,
}

fn collect_candidates_for_dir(
    base_dir: &Path,
    fixed_project: Option<String>,
) -> Vec<FileCandidate> {
    if !base_dir.exists() {
        return Vec::new();
    }

    let base_path_buf = base_dir.to_path_buf();
    let base_check = base_path_buf.clone();

    let mut builder = WalkBuilder::new(base_dir);
    builder
        .standard_filters(false)
        .git_ignore(true)
        .git_global(true)
        .git_exclude(true)
        .parents(true)
        .hidden(false);

    builder.filter_entry(move |entry| {
        let depth = entry.depth();
        if depth == 0 {
            return true;
        }

        let is_dir = entry.file_type().map_or(false, |ft| ft.is_dir());
        let file_name = entry.file_name().to_string_lossy();

        if is_dir {
            // Worktree check: si depth == 1 y existe .git como archivo, descartar
            if depth == 1 {
                let git_marker = entry.path().join(".git");
                if git_marker.is_file() {
                    return false;
                }
            }

            if file_name.starts_with('.') {
                return false;
            }
            if IGNORE_DIRS.contains(file_name.as_ref()) {
                return false;
            }
            if IGNORE_DIR_SUBSTR.iter().any(|s| file_name.contains(s)) {
                return false;
            }
            return true;
        }

        // Para archivos: filtrado rapido por extension y exclusion
        if IGNORE_FILES.contains(file_name.as_ref()) {
            return false;
        }
        if RE_ARCHIVO_SENSIBLE.is_match(file_name.as_ref()) {
            return false;
        }

        let ext = entry
            .path()
            .extension()
            .and_then(|s| s.to_str())
            .map(|s| format!(".{}", s.to_lowercase()))
            .unwrap_or_default();

        if !ALLOWED_EXTENSIONS.contains(ext.as_str()) {
            return false;
        }

        true
    });

    let mut candidates = Vec::new();
    for result in builder.build() {
        let Ok(entry) = result else { continue };
        if entry.file_type().map_or(false, |ft| ft.is_file()) {
            candidates.push(FileCandidate {
                path: entry.into_path(),
                base_dir: base_check.clone(),
                fixed_project: fixed_project.clone(),
            });
        }
    }

    candidates
}

fn process_candidate(candidate: FileCandidate, home: &Path, max_file_size: usize) -> Option<ScannedFile> {
    let path = &candidate.path;
    let metadata = fs::metadata(path).ok()?;
    let size = metadata.len() as usize;

    if size > max_file_size || size == 0 {
        return None;
    }

    let mtime = metadata
        .modified()
        .ok()
        .and_then(|t| t.duration_since(SystemTime::UNIX_EPOCH).ok())
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0);

    let bytes = fs::read(path).ok()?;
    let raw = String::from_utf8_lossy(&bytes);
    let trimmed = raw.trim();
    if trimmed.len() < 10 {
        return None;
    }

    let (content, masked) = mask_secrets(&raw);

    let rel_home = path
        .strip_prefix(home)
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| path.to_string_lossy().to_string());

    let rel_base = path
        .strip_prefix(&candidate.base_dir)
        .unwrap_or(path);

    let project = determine_project(rel_base, &candidate.base_dir, candidate.fixed_project.as_deref());

    let filename = path
        .file_name()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_default();

    let extension = path
        .extension()
        .and_then(|s| s.to_str())
        .map(|s| format!(".{}", s.to_lowercase()))
        .unwrap_or_default();

    Some(ScannedFile {
        path: path.to_string_lossy().to_string(),
        rel_path: rel_home,
        rel_base: rel_base.to_string_lossy().to_string(),
        project,
        filename,
        extension,
        content,
        mtime,
        size,
        secrets_masked: masked,
    })
}

fn process_candidate_metadata(candidate: FileCandidate, home: &Path) -> Option<ScannedFileMetadata> {
    let path = &candidate.path;
    let metadata = fs::metadata(path).ok()?;
    let size = metadata.len() as usize;

    let mtime = metadata
        .modified()
        .ok()
        .and_then(|t| t.duration_since(SystemTime::UNIX_EPOCH).ok())
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0);

    let rel_home = path
        .strip_prefix(home)
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| path.to_string_lossy().to_string());

    let rel_base = path
        .strip_prefix(&candidate.base_dir)
        .unwrap_or(path);

    let project = determine_project(rel_base, &candidate.base_dir, candidate.fixed_project.as_deref());

    let filename = path
        .file_name()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_default();

    let extension = path
        .extension()
        .and_then(|s| s.to_str())
        .map(|s| format!(".{}", s.to_lowercase()))
        .unwrap_or_default();

    Some(ScannedFileMetadata {
        path: path.to_string_lossy().to_string(),
        rel_path: rel_home,
        rel_base: rel_base.to_string_lossy().to_string(),
        project,
        filename,
        extension,
        mtime,
        size,
    })
}

/// Escanea en paralelo multiples directorios, filtra, lee y anonimiza secretos sin GIL
#[pyfunction]
#[pyo3(signature = (scan_directories, max_file_size=None))]
pub fn crawl_directories(
    py: Python<'_>,
    scan_directories: Vec<(String, Option<String>)>,
    max_file_size: Option<usize>,
) -> PyResult<Vec<ScannedFile>> {
    let max_size = max_file_size.unwrap_or(250 * 1024);
    let home = std::env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."));  // sin HOME: rutas relativas al directorio actual

    let results = py.allow_threads(|| {
        let all_candidates: Vec<FileCandidate> = scan_directories
            .into_par_iter()
            .flat_map(|(dir_str, fixed_proj)| {
                let p = Path::new(&dir_str);
                collect_candidates_for_dir(p, fixed_proj)
            })
            .collect();

        all_candidates
            .into_par_iter()
            .filter_map(|cand| process_candidate(cand, &home, max_size))
            .collect()
    });

    Ok(results)
}

/// Escanea en paralelo solo los metadatos de los archivos elegibles sin leer su contenido
#[pyfunction]
pub fn crawl_metadata(
    py: Python<'_>,
    scan_directories: Vec<(String, Option<String>)>,
) -> PyResult<Vec<ScannedFileMetadata>> {
    let home = std::env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."));  // sin HOME: rutas relativas al directorio actual

    let results = py.allow_threads(|| {
        let all_candidates: Vec<FileCandidate> = scan_directories
            .into_par_iter()
            .flat_map(|(dir_str, fixed_proj)| {
                let p = Path::new(&dir_str);
                collect_candidates_for_dir(p, fixed_proj)
            })
            .collect();

        all_candidates
            .into_par_iter()
            .filter_map(|cand| process_candidate_metadata(cand, &home))
            .collect()
    });

    Ok(results)
}

/// Lee, valida y enmascara un archivo unico directamente
#[pyfunction]
#[pyo3(signature = (path, base_dir=None, fixed_project=None, max_file_size=None))]
pub fn read_and_sanitize(
    path: &str,
    base_dir: Option<&str>,
    fixed_project: Option<String>,
    max_file_size: Option<usize>,
) -> PyResult<Option<ScannedFile>> {
    let file_path = PathBuf::from(path);
    let base_path = base_dir.map(PathBuf::from).unwrap_or_else(|| {
        file_path.parent().unwrap_or(&file_path).to_path_buf()
    });

    let home = std::env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."));  // sin HOME: rutas relativas al directorio actual

    let cand = FileCandidate {
        path: file_path,
        base_dir: base_path,
        fixed_project,
    };

    Ok(process_candidate(cand, &home, max_file_size.unwrap_or(250 * 1024)))
}

#[pyfunction]
pub fn get_version() -> &'static str {
    "0.1.0-rust"
}

/// Modulo nativo en Rust para escaneo ultrarrapido de SynRAG
#[pymodule]
fn synrag_crawler(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ScannedFile>()?;
    m.add_class::<ScannedFileMetadata>()?;
    m.add_function(wrap_pyfunction!(mask_secrets, m)?)?;
    m.add_function(wrap_pyfunction!(is_sensitive_file, m)?)?;
    m.add_function(wrap_pyfunction!(should_index, m)?)?;
    m.add_function(wrap_pyfunction!(crawl_directories, m)?)?;
    m.add_function(wrap_pyfunction!(crawl_metadata, m)?)?;
    m.add_function(wrap_pyfunction!(read_and_sanitize, m)?)?;
    m.add_function(wrap_pyfunction!(get_version, m)?)?;
    Ok(())
}
