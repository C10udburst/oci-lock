# oci-lock

> Declarative, reproducible lockfiles for OCI container images — inspired by `flake.lock`.

`oci-lock` manages and pins OCI / Docker container image tags to immutable cryptographic digest hashes (`sha256:...`) in an `oci.lock` file.

Just as `flake.lock` resolves mutable Git branches and tags to exact commit hashes and content hashes for Nix flakes, `oci-lock` resolves mutable container tags (such as `:latest`) to immutable digest references (`image@sha256:...`).

---

## Why?

In NixOS, your entire system configuration is declarative, reproducible, and tracked across generations. However, standard OCI container configurations (e.g. `virtualisation.oci-containers`) often rely on mutable image tags like `:latest`.

This introduces two major issues:
1. **Unpredictable Rebuilds**: Rebuilding your system might pull an updated upstream image with breaking changes or regressions, even if your Nix code didn't change.
2. **Broken Rollbacks**: Standard NixOS rollback (`nixos-rebuild --rollback`) cannot roll back your containers if the tag still points to the broken upstream build.

`oci-lock` bridges this gap:
- **NixOS Rollback for OCI Containers**: Each NixOS generation evaluates against the exact digests pinned in `oci.lock`. Rolling back to an older NixOS generation immediately rolls back your containers to the exact image digests that generation was built with.
- **Truly Hermetic Deployments**: Container pulls become deterministic and reproducible across machines and CI/CD pipelines.
- **Auditable Versioning**: Container image updates become explicit, reviewable Git diffs when running `oci-lock update`.

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
oci-lock add alpine
oci-lock add busybox:latest
```
*(If no tag is specified, `:latest` is assumed).*

#### 2. Remove an Image
Remove an entry from `oci.lock`:
```bash
oci-lock remove alpine
# or using the rm alias
oci-lock rm busybox:latest
```

#### 3. Update All Images
Update all entries in `oci.lock` to their latest registry digests:
```bash
oci-lock update
```
Displays a clear summary of which images were updated and which remained unchanged:
```text
Fetching digest for alpine:latest...
Fetching digest for busybox:latest...

Summary of OCI image locks:
─────────────────────────────
Updated (1):
  • alpine:latest
    alpine@sha256:1234... -> alpine@sha256:28bd...

Unchanged (1):
  • busybox:latest: busybox@sha256:dc2d...
```

#### 4. Update a Specific Image
Update only a single image in `oci.lock`:
```bash
oci-lock update alpine
# or
oci-lock update busybox:latest
```

---

## Lockfile Format (`oci.lock`)

The generated `oci.lock` is clean, sorted JSON mapping mutable image tags to immutable digest specifications:

```json
{
  "alpine:latest": "alpine@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b",
  "busybox:latest": "busybox@sha256:dc2d74b28e4cf8984fa52af1f39bc7c3d9c73760b41a74d629f5d11b1ab28616"
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
  virtualisation.oci-containers.containers.alpine = {
    image = resolveImage "alpine:latest";
    cmd = [ "echo" "hello from locked alpine" ];
  };
}
```

---

## License

MIT License © 2026 Cloudburst
