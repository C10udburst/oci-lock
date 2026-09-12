{
  description = "oci-lock: Lock OCI container image versions";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-26.05";
  };

  outputs =
    { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          oci-lock = pkgs.stdenv.mkDerivation {
            pname = "oci-lock";
            version = "0.1.0";
            src = ./.;
            nativeBuildInputs = [ pkgs.makeWrapper ];
            propagatedBuildInputs = [
              pkgs.python3
              pkgs.crane
            ];
            installPhase = ''
              mkdir -p $out/bin
              cp oci_lock.py $out/bin/oci-lock
              chmod +x $out/bin/oci-lock
              wrapProgram $out/bin/oci-lock \
                --prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.python3 pkgs.crane ]}
            '';
          };
          default = self.packages.${system}.oci-lock;
        }
      );

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/oci-lock";
        };
      });
    };
}
