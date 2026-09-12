# oci-lock

> Declarative, reproducible lockfiles for OCI container images — inspired by `flake.lock`.

`oci-lock` manages and pins OCI / Docker container image tags to immutable cryptographic digest hashes (`sha256:...`) in an `oci.lock` file.

Just as `flake.lock` resolves mutable Git branches and tags to exact commit hashes and content hashes for Nix flakes, `oci-lock` resolves mutable container tags (such as `:latest`) to immutable digest references (`image@sha256:...`).

---

## Features

- **Immutable Pinning**: Locks mutable tags (`image:latest`) to exact, content-addressed OCI digests (`image@sha256:<digest>`).
- **Reproducibility**: Guarantees identical container pulls across rebuilds and deployments, avoiding unexpected breakage from upstream updates.
- **Fast & Lightweight**: Leverages [`crane`](https://github.com/google/go-containerregistry/tree/main/cmd/crane) to fetch digests directly from registries without pulling image layers.
- **Clear Diff Summaries**: `oci-lock update` reports precisely which image digests changed and which remained unchanged.
- **Drop-in Nix Integration**: Easily parsed by Nix via `builtins.fromJSON (builtins.readFile ./oci.lock)` for NixOS `virtualisation.oci-containers` or Kubernetes manifests.

---

## Installation & Usage

### Run Directly via Nix Flakes

Without installing:
```bash
nix run github:C10udburst/oci-lock -- --help
```

Or drop into an ephemeral shell:
```bash
nix shell github:C10udburst/oci-lock
```

### CLI Commands

#### 1. Add an Image
Add a container image to `oci.lock` in the current directory:
```bash
oci-lock add b3log/siyuan
oci-lock add ghcr.io/homarr-labs/homarr:latest
```
*(If no tag is specified, `:latest` is assumed).*

#### 2. Update All Images
Update all entries in `oci.lock` to their latest registry digests:
```bash
oci-lock update
```
Displays a clear summary of which images were updated and which remained unchanged:
```text
Fetching digest for b3log/siyuan:latest...
Fetching digest for ghcr.io/homarr-labs/homarr:latest...

Summary of OCI image locks:
─────────────────────────────
Updated (1):
  • b3log/siyuan:latest
    b3log/siyuan@sha256:5a4f... -> b3log/siyuan@sha256:6ab1...

Unchanged (1):
  • ghcr.io/homarr-labs/homarr:latest: ghcr.io/homarr-labs/homarr@sha256:1f5b...
```

#### 3. Update a Specific Image
Update only a single image in `oci.lock`:
```bash
oci-lock update b3log/siyuan
# or
oci-lock update ghcr.io/homarr-labs/homarr:latest
```

---

## Lockfile Format (`oci.lock`)

The generated `oci.lock` is clean, sorted JSON mapping mutable image tags to immutable digest specifications:

```json
{
  "b3log/siyuan:latest": "b3log/siyuan@sha256:6ab17ed3ca40f646eab674f3fdcc459ff186614c02434b9b07709bd4cc98716d",
  "ghcr.io/homarr-labs/homarr:latest": "ghcr.io/homarr-labs/homarr@sha256:1f5b892aeef4ad0a4907f075777bbd0ce7120f4cdc53b9f3f028519250421aed",
  "ghcr.io/manyfold3d/manyfold-solo:latest": "ghcr.io/manyfold3d/manyfold-solo@sha256:f620fe830c8964abb0c6ab9c35ae58a3e7426e939adddbba9def12dd618b4d42",
  "ghcr.io/transmute-app/transmute:latest": "ghcr.io/transmute-app/transmute@sha256:51a32b28e0cb84cde624ca41570f069d91ee7e83fac5c9d0b970e7a583b3abde",
  "wealthfolio/wealthfolio:latest": "wealthfolio/wealthfolio@sha256:3c6f117828949204029c2b4a391f039e62987b4e091139e11b04e6764b5f6866"
}
```

---

## NixOS Integration Example

In your NixOS configuration or module:

```nix
{ config, lib, pkgs, ... }:
let
  ociLock =
    let
      lockPath = ./oci.lock;
    in
    if builtins.pathExists lockPath then
      builtins.fromJSON (builtins.readFile lockPath)
    else
      { };

  resolveImage = image: ociLock.${image} or image;
in
{
  virtualisation.oci-containers.containers.homarr = {
    image = resolveImage "ghcr.io/homarr-labs/homarr:latest";
    ports = [ "7575:7575" ];
  };
}
```

---

## License

MIT License © 2026 Cloudburst
