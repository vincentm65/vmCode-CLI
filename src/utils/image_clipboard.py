"""Cross-platform clipboard image reader for prompt image paste."""

from __future__ import annotations

import imghdr
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


MAX_CLIPBOARD_IMAGE_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class ClipboardImage:
    """Image data read from the clipboard."""

    data: bytes
    mime_type: str


@dataclass(frozen=True)
class ClipboardImageResult:
    """Structured clipboard image read result."""

    image: Optional[ClipboardImage] = None
    reason: Optional[str] = None
    message: str = ""


_IMAGE_MIME_TYPES = (
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "public.png",
    "public.jpeg",
    "public.webp",
    "com.compuserve.gif",
)

_MIME_ALIASES = {
    "public.png": "image/png",
    "public.jpeg": "image/jpeg",
    "public.webp": "image/webp",
    "com.compuserve.gif": "image/gif",
}

_EXTENSION_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

_DETECTED_MIME_TYPES = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}


def _normalise_mime_type(mime_type: str) -> str:
    return _MIME_ALIASES.get(mime_type, mime_type)


def _session_type() -> str:
    return (os.environ.get("XDG_SESSION_TYPE") or "").lower()


def _image_result(data: bytes, mime_type: str) -> ClipboardImageResult:
    if not data:
        return ClipboardImageResult(reason="no_image")
    if len(data) > MAX_CLIPBOARD_IMAGE_BYTES:
        return ClipboardImageResult(reason="too_large", message="Clipboard image is larger than 10 MB.")
    return ClipboardImageResult(image=ClipboardImage(data=data, mime_type=_normalise_mime_type(mime_type)))


def _mime_type_for_path(path: Path, data: bytes) -> Optional[str]:
    extension_mime = _EXTENSION_MIME_TYPES.get(path.suffix.lower())
    if extension_mime:
        return extension_mime
    detected = imghdr.what(None, h=data)
    return _DETECTED_MIME_TYPES.get(detected or "")


def read_image_file(path: str | Path) -> ClipboardImageResult:
    """Read a supported image file from disk as an attachment."""
    image_path = Path(path).expanduser()
    if not image_path.exists():
        return ClipboardImageResult(reason="not_found", message=f"Image file not found: {image_path}")
    if not image_path.is_file():
        return ClipboardImageResult(reason="not_file", message=f"Image path is not a file: {image_path}")

    try:
        data = image_path.read_bytes()
    except OSError as exc:
        return ClipboardImageResult(reason="read_error", message=f"Could not read image file: {exc}")

    mime_type = _mime_type_for_path(image_path, data)
    if not mime_type:
        return ClipboardImageResult(
            reason="unsupported_type",
            message="Supported image files: .png, .jpg, .jpeg, .webp, .gif.",
        )
    return _image_result(data, mime_type)


def _run(command: list[str], *, timeout: int = 5) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def _decode_stderr(result: subprocess.CompletedProcess[bytes]) -> str:
    return result.stderr.decode("utf-8", errors="replace").strip()


def _detect_wayland_mime() -> Optional[str]:
    try:
        result = _run(["wl-paste", "--list-types"], timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    types = result.stdout.decode("utf-8", errors="replace").splitlines()
    return next((mime for mime in _IMAGE_MIME_TYPES if mime in types), None)


def _read_wayland_image() -> ClipboardImageResult:
    if not shutil.which("wl-paste"):
        return ClipboardImageResult(
            reason="missing_tool",
            message="Install wl-clipboard to paste images on Wayland.",
        )

    mime_type = _detect_wayland_mime()
    if not mime_type:
        return ClipboardImageResult(reason="no_image")

    try:
        result = _run(["wl-paste", "--no-newline", "--type", mime_type])
    except subprocess.TimeoutExpired:
        return ClipboardImageResult(reason="clipboard_error", message="Timed out reading clipboard image.")
    except OSError as exc:
        return ClipboardImageResult(reason="clipboard_error", message=str(exc))

    if result.returncode != 0:
        return ClipboardImageResult(reason="clipboard_error", message=_decode_stderr(result))
    return _image_result(result.stdout, mime_type)


def _read_x11_image() -> ClipboardImageResult:
    if not shutil.which("xclip"):
        return ClipboardImageResult(
            reason="missing_tool",
            message="Install xclip to paste images on X11.",
        )

    for mime_type in _IMAGE_MIME_TYPES:
        try:
            result = _run(["xclip", "-selection", "clipboard", "-t", mime_type, "-o"])
        except subprocess.TimeoutExpired:
            return ClipboardImageResult(reason="clipboard_error", message="Timed out reading clipboard image.")
        except OSError as exc:
            return ClipboardImageResult(reason="clipboard_error", message=str(exc))

        if result.returncode == 0 and result.stdout:
            return _image_result(result.stdout, mime_type)

    return ClipboardImageResult(reason="no_image")


def _read_macos_image() -> ClipboardImageResult:
    if not shutil.which("osascript"):
        return ClipboardImageResult(reason="missing_tool", message="osascript is required to paste images on macOS.")

    with tempfile.TemporaryDirectory(prefix="bone-clipboard-") as tmp_dir:
        output_path = Path(tmp_dir) / "clipboard.png"
        escaped_path = str(output_path).replace("\\", "\\\\").replace('"', '\\"')
        script = (
            f"set outputPath to POSIX file \"{escaped_path}\"\n"
            "try\n"
            "  set imageData to the clipboard as «class PNGf»\n"
            "  set fileRef to open for access outputPath with write permission\n"
            "  set eof fileRef to 0\n"
            "  write imageData to fileRef\n"
            "  close access fileRef\n"
            "  return \"ok\"\n"
            "on error errMsg\n"
            "  try\n"
            "    close access outputPath\n"
            "  end try\n"
            "  return \"no_image\"\n"
            "end try\n"
        )
        try:
            result = _run(["osascript", "-e", script])
        except subprocess.TimeoutExpired:
            return ClipboardImageResult(reason="clipboard_error", message="Timed out reading clipboard image.")
        except OSError as exc:
            return ClipboardImageResult(reason="clipboard_error", message=str(exc))

        if result.returncode != 0:
            return ClipboardImageResult(reason="clipboard_error", message=_decode_stderr(result))
        if result.stdout.decode("utf-8", errors="replace").strip() != "ok" or not output_path.exists():
            return ClipboardImageResult(reason="no_image")
        return _image_result(output_path.read_bytes(), "image/png")


def _read_windows_image() -> ClipboardImageResult:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if not powershell:
        return ClipboardImageResult(reason="missing_tool", message="PowerShell is required to paste images on Windows.")

    with tempfile.TemporaryDirectory(prefix="bone-clipboard-") as tmp_dir:
        output_path = Path(tmp_dir) / "clipboard.png"
        escaped_path = str(output_path).replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            "if (-not [System.Windows.Forms.Clipboard]::ContainsImage()) { exit 2 }; "
            "$image = [System.Windows.Forms.Clipboard]::GetImage(); "
            f"$image.Save('{escaped_path}', [System.Drawing.Imaging.ImageFormat]::Png)"
        )
        try:
            result = _run([powershell, "-NoProfile", "-STA", "-Command", script])
        except subprocess.TimeoutExpired:
            return ClipboardImageResult(reason="clipboard_error", message="Timed out reading clipboard image.")
        except OSError as exc:
            return ClipboardImageResult(reason="clipboard_error", message=str(exc))

        if result.returncode == 2:
            return ClipboardImageResult(reason="no_image")
        if result.returncode != 0:
            return ClipboardImageResult(reason="clipboard_error", message=_decode_stderr(result))
        if not output_path.exists():
            return ClipboardImageResult(reason="no_image")
        return _image_result(output_path.read_bytes(), "image/png")


def _read_linux_image() -> ClipboardImageResult:
    if _session_type() == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
        result = _read_wayland_image()
        if result.reason != "missing_tool":
            return result

    if os.environ.get("DISPLAY"):
        return _read_x11_image()

    return ClipboardImageResult(
        reason="unsupported_platform",
        message="Image paste needs Wayland wl-clipboard or X11 xclip in this Linux session.",
    )


def read_clipboard_image() -> ClipboardImageResult:
    """Read an image from the system clipboard, if one is available."""
    system = platform.system()
    if system == "Linux":
        return _read_linux_image()
    if system == "Darwin":
        return _read_macos_image()
    if system == "Windows":
        return _read_windows_image()
    return ClipboardImageResult(reason="unsupported_platform", message=f"Image paste is not supported on {system or 'this platform'}.")
