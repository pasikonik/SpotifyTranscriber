{pkgs}: {
  deps = [
    pkgs.firefox-esr
    pkgs.chromium
    pkgs.playwright-driver
    pkgs.gitFull
    pkgs.postgresql
    pkgs.openssl
  ];
}
