{
  description = "Venera: Direct3D, Vulkan and OpenGL for Windows guests on QEMU + Venus";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      mingw = pkgs.pkgsCross.mingwW64;
      mcfg = mingw.windows.mcfgthreads;
      # The 32-bit UMDs and Mesa drivers, for 32-bit processes (the *Wow entries in pkg/venera.inf).
      mingw32 = pkgs.pkgsCross.mingw32;
      mcfg32 = mingw32.windows.mcfgthreads;
      # GCC does not target Windows on Arm. Keep LLVM-MinGW's compiler and runtime
      # together, including the libraries linked into DXVK, vkd3d-proton and Mesa.
      llvmMingw = pkgs.stdenvNoCC.mkDerivation {
        pname = "llvm-mingw";
        version = "20251104";
        src = pkgs.fetchurl {
          url = "https://github.com/mstorsjo/llvm-mingw/releases/download/20251104/llvm-mingw-20251104-ucrt-ubuntu-22.04-x86_64.tar.xz";
          sha256 = "3aed6fa47be909884cb3e5634d6b7254604d7104832d6312f8435fb23d5a9bab";
        };
        nativeBuildInputs = [ pkgs.autoPatchelfHook ];
        buildInputs = [ pkgs.stdenv.cc.cc.lib pkgs.zlib ];
        dontConfigure = true;
        dontBuild = true;
        # Target PE DLLs and archives are already built; only host ELF tools need
        # their interpreter and library search paths adjusted for the Nix store.
        dontStrip = true;
        installPhase = ''
          runHook preInstall
          mkdir -p "$out"
          cp -a . "$out/"
          runHook postInstall
        '';
      };
      # vkd3d-proton generates its D3D12 headers from IDL with widl. nixpkgs ships widl only with Wine: expose just
      # that binary, so wine itself stays off PATH.
      widl = pkgs.runCommand "widl" { } ''
        mkdir -p $out/bin
        ln -s ${pkgs.wine64Packages.minimal}/bin/widl $out/bin/widl
      '';
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          cmake ninja pkg-config
          unzip osslsigncode wimlib
          # Mesa (icd/build.sh): meson and its Python code generators.
          meson bison flex
          (python3.withPackages (p: [ p.mako p.pyyaml p.packaging ]))
          # vkd3d-proton (third_party/vkd3d-proton): IDL headers and its internal GLSL shaders.
          widl glslang
          mingw.buildPackages.gcc
          mingw.buildPackages.binutils
          mingw32.buildPackages.gcc
          mingw32.buildPackages.binutils
          # Wraps the MinGW compilers when on PATH (icd/build.sh, CMakeLists.txt, cmake/meson.cmake).
          ccache
          # Puts the installer on a disc image (.github/workflows/build.yml).
          xorriso
        ];

        # Every store path has the same mtime, so ccache's default check would miss a compiler update: hash the
        # compiler (the wrapper script, which names the GCC it runs) instead.
        CCACHE_COMPILERCHECK = "content";

        # Read by cmake/mingw-w64*.cmake and icd/build.sh: GCC from nixpkgs uses the mcfgthread model,
        # whose headers and static library live outside the wrapper's default paths.
        VENERA_MINGW_MCFG_INCLUDE = "${mcfg.dev}/include";
        VENERA_MINGW_MCFG_LIB = "${mcfg}/lib";
        VENERA_MINGW32_MCFG_INCLUDE = "${mcfg32.dev}/include";
        VENERA_MINGW32_MCFG_LIB = "${mcfg32}/lib";
        VENERA_LLVM_MINGW_ROOT = "${llvmMingw}";

        # Read by cmake/clang-cl-kmd.cmake. Not on PATH: unwrapped clang would shadow the host cc/cpp.
        VENERA_CLANG_CL = "${pkgs.llvmPackages.clang-unwrapped}/bin/clang-cl";
        VENERA_LLD_LINK = "${pkgs.lld}/bin/lld-link";
        VENERA_LLVM_RC = "${pkgs.llvmPackages.llvm}/bin/llvm-rc";
        VENERA_LLVM_LIB = "${pkgs.llvmPackages.llvm}/bin/llvm-lib";
      };
    };
}
