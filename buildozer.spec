[app]
title = Among Us Deduction Panel
package.name = amongusdeduction
package.domain = org.teahacktools
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0

# Buildozer compiles the Android package on Linux (or WSL2).
# No broad storage permission is required: match JSON stays in app-private storage.
android.api = 35
android.minapi = 24
android.ndk = 27c
android.ndk_api = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
