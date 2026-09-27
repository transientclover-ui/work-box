"""Explicit per-user menu registration for pip/uv installations."""
import argparse
from importlib.resources import files
import os
from pathlib import Path
import sys
import sysconfig


def quote_exec(path: Path) -> str:
    """Quote an executable using Desktop Entry string and Exec escaping."""
    value = str(path)
    if '=' in value or any(c in value for c in '\n\r\t'):
        raise ValueError('Installation path cannot contain =, tabs or newlines')
    value = value.replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\' + char)
    return '"' + value.replace('\\', '\\\\') + '"'


def install(executable: Path | None = None) -> Path:
    if executable is None:
        executable = Path(sysconfig.get_path('scripts')) / 'work-box'
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError(f'No installed executable at {executable}; install work-box first')
    data = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    if not data.is_absolute():
        raise ValueError('XDG_DATA_HOME must be an absolute path')
    template = files('workbox').joinpath('work-box.desktop')
    # Editable source installs keep the canonical template outside the package.
    if not template.is_file():
        template = Path(__file__).resolve().parents[2] / 'share/work-box.desktop'
    content = template.read_text(encoding='utf-8').replace(
        'Exec=work-box\n', f'Exec={quote_exec(executable)}\n')
    target = data / 'applications/work-box.desktop'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    return target


def main():
    parser = argparse.ArgumentParser(description='Install the Work Box application-menu entry for this user.')
    parser.parse_args()
    try:
        # Follow a uv/pipx exposed helper symlink to its persistent environment.
        helper = Path(sys.argv[0]).resolve()
        executable = helper.with_name('work-box') if helper.name == 'work-box-desktop' else None
        target = install(executable)
    except (OSError, ValueError) as error:
        print(f'work-box-desktop: {error}', file=sys.stderr)
        return 1
    print(f'Installed {target}')
    print('Search for Work Box in your application launcher. Rerun after moving/reinstalling the environment.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
