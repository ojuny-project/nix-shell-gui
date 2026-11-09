# nix-shell-gui

nix-shell-gui is a GTK3 application for browsing nixpkgs and launching packages
without installing them. It searches the nixpkgs flake, marks packages already
present in `/nix/store`, stores favourites, and starts a selected package with
`nix run` or `nix shell`. The package targets Linux and uses Python 3.9 or newer.

## Status

Untested. The version in `pyproject.toml` and `flake.nix` is 0.1.0. The pytest
suite covers classification, search parsing, store state, and terminal command
expansion, but no manual run is recorded for this page.

## Requirements

- Nix with flakes enabled and `nix` on `PATH`.
- Network access to the nixpkgs flake for `nix search`, or a warm store and a
  populated search cache.
- GTK3 and PyGObject at runtime; the package supplies both.
- One of `ghostty`, `kitty`, `alacritty`, `foot`, or `xterm` for packages that
  need a terminal. A missing terminal leaves the launch command unrunnable.

Disk and memory requirements are not stated.

## Install

Run the application directly:

```console
$ nix run github:ojuny-project/nix-shell-gui
```

The window titled `Nix App Store` opens. On first start the status line reads
`Loading package index...`; after the search completes it reports a result count
in the form `<number> results`.

To install it into a NixOS system, add the flake input and enable the module:

```nix
{
  inputs.nix-shell-gui.url = "github:ojuny-project/nix-shell-gui";

  outputs = inputs@{ nixpkgs, ... }: {
    nixosConfigurations.host = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        inputs.nix-shell-gui.nixosModules.default
        { services.nix-shell-gui.enable = true; }
      ];
    };
  };
}
```

Rebuild with `sudo nixos-rebuild switch --flake .#<host>`. The module adds the
package to `environment.systemPackages`; `command -v nix-shell-gui` prints the
installed path.

## Usage

Type in the search box to filter by attribute path, name, or description. The
`Offline only` checkbox keeps packages whose names match entries in
`/nix/store`; `Favourites` keeps the packages you starred. Select a package to
see its version, description, and detected launch mode.

Press Launch. A package classified as a GUI application runs
`nix run nixpkgs#<attr>` with no terminal. A TUI application runs the same
command in a terminal window. Everything else opens `nix shell nixpkgs#<attr>`
in a terminal, so the command is available in an interactive shell. No package
is added to a profile.

Favourites and caches live under `~/.config/nix-shell-gui/`:
`favourites.json`, `catalog.json`, and `offline.json`. To choose another
terminal, create `config.json` there:

```json
{
  "terminal": ["kitty", "--", "{command}"]
}
```

`{command}` is replaced by the argument list; `{command_s}` is replaced by a
single shell-quoted string.

## Limits

Classification is a heuristic. It reads a desktop file when the package is
already in the store, then checks build input names for GUI or TUI libraries,
and otherwise falls back to the shell mode. A misclassified package may open
the wrong launcher. The catalogue comes from `nix search nixpkgs` and can be
stale until the next successful load. The application does not install,
remove, or update packages, does not manage channels, and does not provide
access control. Launching needs network access unless every store path is
already present. There is no launch progress or cancel control.

## Releases

A `v*` tag, a manual workflow run, or a commit on `main` whose title starts with
a version such as `v0.1.0` builds `nix-shell-gui.bin` and `nix-shell-gui-flake.tar.gz`.

The release flake installs the prebuilt bundle without compiling:

```nix
inputs.nix-shell-gui.url =
  "tarball+https://github.com/ojuny-project/nix-shell-gui/releases/download/vX.Y.Z/nix-shell-gui-flake.tar.gz";
```

Then add `inputs.nix-shell-gui.packages.${pkgs.system}.nix-shell-gui` to `environment.systemPackages`.

The generated flake exposes packages only. Use the source flake when you need
the NixOS module.


## Documentation
- [OPTIONS.md](OPTIONS.md) is the generated options reference.

- [flake.nix](flake.nix) lists the package, app, devshell, check, and module.
- [src/nix_shell_gui/classify.py](src/nix_shell_gui/classify.py) shows the launch-mode rules.
- [src/nix_shell_gui/terminal.py](src/nix_shell_gui/terminal.py) shows the terminal templates and commands.
- [src/nix_shell_gui/store.py](src/nix_shell_gui/store.py) shows the cache and favourites files.
- [src/nix_shell_gui/search.py](src/nix_shell_gui/search.py) shows the nix search call and parsing.

## Contributing

Open issues at <https://github.com/ojuny-project/nix-shell-gui/issues>. A patch
must add or update a pytest case, run `pytest` from `nix develop`, and keep
`nix flake check` passing.

## License

GNU General Public License version 3. The repository states no later-version
grant. See [LICENSE](LICENSE).

