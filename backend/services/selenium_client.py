from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import WebDriverException
import threading
import os
import time
from pathlib import Path


class WebBrowserManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WebBrowserManager, cls).__new__(cls)
                cls._instance.driver = None
                cls._instance._init_driver()
        return cls._instance

    def _clear_stale_profile_locks(self, profile_path: str) -> None:
        """Remove stale Firefox profile locks if no Firefox is alive.

        Firefox guards a profile with three possible lock artefacts:

          * ``parent.lock`` — Windows; zero-byte sentinel file
          * ``.parentlock`` — POSIX equivalent
          * ``lock``        — POSIX symlink to ``ip:pid`` of the owner

        When a previous Firefox child is force-killed (e.g. by
        ``reset_state.py --kill`` or a hard reboot), these files
        survive and the next launch sees the lock, prints
        ``"Firefox is already running"`` to its own stderr, and exits
        cleanly — geckodriver then reports
        ``"Process unexpectedly closed with status 0"`` and the mapper
        boots with no driver attached.

        Strategy: try to ``unlink()`` each lock. On Windows, the unlink
        will raise ``PermissionError`` if a live Firefox process has it
        open — in which case we leave it alone and surface a warning,
        because killing that live Firefox here would discard the user's
        browsing state. Otherwise the unlink succeeds and Firefox boots
        clean on the next attempt.
        """
        candidates = ["parent.lock", ".parentlock", "lock"]
        cleared, blocked = [], []
        for fname in candidates:
            p = Path(profile_path) / fname
            try:
                if not p.exists() and not p.is_symlink():
                    continue
            except OSError:
                continue
            try:
                p.unlink()
                cleared.append(fname)
            except PermissionError:
                blocked.append(fname)
            except FileNotFoundError:
                continue
            except OSError as e:
                blocked.append(f"{fname} ({e.__class__.__name__})")
        if cleared:
            print(f"[Selenium] Removed stale profile lock(s): {', '.join(cleared)}")
        if blocked:
            print(f"[Selenium] WARNING: profile lock(s) held by a live process: "
                  f"{', '.join(blocked)}. Close any open Firefox window using "
                  f"this profile, or run `python scripts/reset_state.py --kill`.")

    def _find_binary(self, name: str, env_var: str, default_paths: list) -> str:
        """Locate a binary: env override -> default_paths -> PATH fallback."""
        # Environment override
        env_path = os.environ.get(env_var)
        if env_path and Path(env_path).exists():
            return env_path
        # Check default paths
        for p in default_paths:
            if Path(p).exists():
                return p
        # Try to find it on PATH (or just return the name)
        return name  # let the OS resolve it

    def _init_driver(self):
        print("[Selenium] Initializing Firefox WebDriver (HEADFUL)…")
        options = Options()

        # The browser MUST be headful. The user navigates the live
        # window themselves and clicks "Snapshot Live Browser" to
        # capture whatever page they're viewing. A headless driver
        # silently breaks that workflow because the user can't see
        # or interact with the page. We assert this defensively in
        # case any future commit accidentally flips it.
        assert "--headless" not in (options.arguments or []), (
            "Firefox MUST run headful so the user can navigate and "
            "trigger snapshots manually — never set --headless here."
        )
        try:
            options.headless = False
        except Exception:
            pass

        options.add_argument("--width=1280")
        options.add_argument("--height=900")

        # Disable the navigator.webdriver flag so JS-driven SPAs (Angular,
        # React with bot guards) actually bootstrap. archive.org's Angular
        # shell silently refuses to render <app-root> when navigator.webdriver
        # is true — empty body, zero text, zero chunks. This pref + the
        # CDP-style override below makes navigator.webdriver === undefined.
        try:
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)
            # Pretend we're a normal Firefox install (some sniffers also
            # check the marionette flag indirectly via prefs).
            options.set_preference("marionette.enabled", True)  # keep driver alive
            # Realistic UA — geckodriver default is fine, but some sites
            # geo-throttle Selenium-shaped UAs. Leave default; only override
            # if a future scan target needs it.
        except Exception:
            pass

        # Fallback profile setup — keep the user's logged-in
        # accounts and uBlock filters available in the live window.
        # Skipped when WFH_NO_PROFILE=1 is set (e.g. by scan.py) so
        # standalone scans get a clean browser. Some target SPAs (the
        # Angular app on archive.org, in particular) fail to bootstrap
        # when uBlock blocks one of their bundle's dependencies, leaving
        # an empty <app-root> with bodyTextLen=0 and zero chunks emitted.
        try:
            if os.environ.get("WFH_NO_PROFILE") != "1":
                profile_path = r"C:\Users\isaac\AppData\Roaming\Mozilla\Firefox\Profiles\iwunpegz.ublock"
                if os.path.exists(profile_path):
                    # Scrub stale profile locks (parent.lock /.parentlock /lock)
                    # left behind when a previous Firefox child was killed
                    # without a graceful shutdown. Symptom: geckodriver
                    # immediately emits "Process unexpectedly closed with
                    # status 0" because Firefox sees the lock, assumes the
                    # profile is in use, and exits cleanly.
                    self._clear_stale_profile_locks(profile_path)
                    options.add_argument("-profile")
                    options.add_argument(profile_path)
                    print(f"[Selenium] Using profile: {profile_path}")
                else:
                    print("[Selenium] No saved profile found — using default.")
            else:
                print("[Selenium] WFH_NO_PROFILE=1 — skipping user profile (clean browser).")
        except Exception:
            pass

        # --- Locate Firefox browser binary ---
        firefox_bin = self._find_binary(
            "firefox",
            "FIREFOX_BINARY_PATH",
            [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
                os.path.expanduser(r"~\AppData\Local\Mozilla Firefox\firefox.exe"),
            ],
        )
        options.binary_location = firefox_bin
        print(f"[Selenium] Using firefox binary: {firefox_bin}")

        # --- Locate geckodriver binary ---
        driver_path = self._find_binary(
            "geckodriver",
            "GECKO_DRIVER_PATH",
            [
                str(Path(__file__).resolve().parent.parent.parent / "backend" / "drivers" / "geckodriver.exe"),
                # Also search common cache locations
                *[str(p) for p in Path.home().glob(".wdm/drivers/geckodriver/**/geckodriver.exe")],
            ],
        )
        if not Path(driver_path).exists():
            print("[Selenium] Local geckodriver not found — downloading via webdriver-manager…")
            try:
                driver_path = GeckoDriverManager().install()
            except Exception as e:
                raise RuntimeError(
                    "Could not obtain geckodriver. "
                    "Place geckodriver.exe in backend/drivers/ "
                    "or set GECKO_DRIVER_PATH environment variable."
                ) from e
        else:
            print(f"[Selenium] Using local geckodriver: {driver_path}")

        self.driver = webdriver.Firefox(
            service=FirefoxService(executable_path=driver_path),
            options=options,
        )
        
    def get_driver(self):
        """Get a healthy driver. Auto-reconnect if needed."""
        with self._lock:
            if self.driver is None or not self._is_alive():
                self._reconnect()
            return self.driver

    def _is_alive(self) -> bool:
        """Cheap health check via current_url access."""
        try:
            _ = self.driver.current_url
            return True
        except (WebDriverException, AttributeError):
            return False

    def _reconnect(self, max_attempts: int = 3):
        """Tear down and restart WebDriver."""
        for attempt in range(max_attempts):
            try:
                if self.driver:
                    try: self.driver.quit()
                    except Exception: pass
                self._init_driver()
                print(f"[Selenium] WebDriver reconnected on attempt {attempt + 1}")
                return
            except Exception as e:
                print(f"[Selenium] WebDriver reconnect attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)
        raise RuntimeError("WebDriver reconnect failed after retries")
        
    def get_page_source(self) -> str:
        """ Returns the current raw HTML of whatever page the user is viewing. """
        driver = self.get_driver()
        if driver:
            return driver.page_source
        return ""
        
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
