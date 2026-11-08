"""
Among Us Deduction Panel - Android edition
Built with Kivy. Match data is stored locally in the app's private data folder.
This is a manual companion tool; it does not connect to or modify Among Us.
"""
from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime
from typing import Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.graphics import Color, RoundedRectangle

APP_TITLE = "Among Us Deduction Panel"
ROOMS = [
    "Cafeteria", "Weapons", "O2", "Navigation", "Shields",
    "Communications", "Storage", "Admin", "Electrical",
    "Lower Engine", "Upper Engine", "Security", "MedBay",
    "Reactor", "Launchpad", "Laboratory", "Office",
    "Greenhouse", "Balcony", "Specimen", "Other"
]
COLORS = {
    "Red": "#ef4444", "Blue": "#3b82f6", "Green": "#22c55e",
    "Pink": "#ec4899", "Orange": "#f97316", "Yellow": "#eab308",
    "Black": "#64748b", "White": "#e2e8f0", "Purple": "#a855f7",
    "Cyan": "#06b6d4", "Brown": "#a16207", "Lime": "#84cc16",
    "Maroon": "#991b1b", "Rose": "#fb7185", "Banana": "#fde047",
    "Gray": "#9ca3af", "Tan": "#d6b58c", "Coral": "#fb7185"
}
STATUSES = ["Alive", "Dead", "Ejected", "Cleared"]
FLAGS = {
    "Faking common task": 18, "Vented": 24, "Avoided task": 8,
    "Seen near body": 10, "False information": 16,
    "Other concern": 8, "Manual suspicion": 6
}
EDGES = {
    ("Cafeteria", "Weapons"): 8, ("Cafeteria", "O2"): 8,
    ("Cafeteria", "Admin"): 10, ("Weapons", "Navigation"): 7,
    ("O2", "Navigation"): 9, ("O2", "Shields"): 8,
    ("Shields", "Navigation"): 7, ("Shields", "Communications"): 8,
    ("Communications", "Storage"): 9, ("Storage", "Admin"): 8,
    ("Storage", "Electrical"): 10, ("Storage", "Lower Engine"): 9,
    ("Electrical", "Lower Engine"): 8, ("Lower Engine", "Reactor"): 9,
    ("Upper Engine", "Reactor"): 8, ("Upper Engine", "MedBay"): 8,
    ("MedBay", "Security"): 8, ("Security", "Reactor"): 10,
    ("Cafeteria", "Upper Engine"): 9,
    ("Launchpad", "Laboratory"): 9, ("Laboratory", "Office"): 8,
    ("Office", "Greenhouse"): 8, ("Office", "Balcony"): 7,
    ("Laboratory", "Specimen"): 10, ("Specimen", "Office"): 10,
}


def clock_text():
    return datetime.now().strftime("%H:%M:%S")


def to_seconds(value: str) -> Optional[int]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        if ":" in value:
            m, s = map(int, value.split(":"))
            return m * 60 + s if m >= 0 and 0 <= s < 60 else None
        number = int(value)
        return number if number >= 0 else None
    except (ValueError, TypeError):
        return None


def shortest_time(start, end):
    if start == end:
        return 0
    graph = {}
    for (a, b), cost in EDGES.items():
        graph.setdefault(a, []).append((b, cost))
        graph.setdefault(b, []).append((a, cost))
    if start not in graph or end not in graph:
        return None
    dist, todo, seen = {start: 0}, [(0, start)], set()
    while todo:
        todo.sort(reverse=True)
        cost, room = todo.pop()
        if room in seen:
            continue
        seen.add(room)
        if room == end:
            return cost
        for nxt, weight in graph.get(room, []):
            candidate = cost + weight
            if candidate < dist.get(nxt, math.inf):
                dist[nxt] = candidate
                todo.append((candidate, nxt))
    return None


class Player:
    def __init__(self, name, color, status="Alive", flags=None):
        self.name = name
        self.color = color
        self.status = status
        self.flags = list(flags or [])

    def data(self):
        return {"name": self.name, "color": self.color,
                "status": self.status, "flags": self.flags}


class DeductionApp(App):
    def build(self):
        self.title = APP_TITLE
        self.players = [
            Player(f"Player {i+1}", color)
            for i, color in enumerate([
                "Red", "Blue", "Green", "Pink", "Orange",
                "Yellow", "Black", "White", "Purple", "Cyan"
            ])
        ]
        self.locations = []
        self.claims = []
        self.events = []
        self.round_no = 1
        self.score_data = {}
        self.notes = ""

        root = BoxLayout(orientation="vertical", spacing=dp(5), padding=dp(8))
        with root.canvas.before:
            Color(0.035, 0.065, 0.12, 1)
            self.bg_rect = RoundedRectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        header = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        header.add_widget(Label(
            text="[b]◉  DEDUCTION PANEL[/b]\\n[size=10sp]ANDROID MATCH TRACKER[/size]",
            markup=True, halign="left", valign="middle", color=(0.4, 0.9, 1, 1)
        ))
        header.add_widget(self.small_button("Save", self.save_match, width=dp(75)))
        header.add_widget(self.small_button("Load", self.load_match, width=dp(75)))
        root.add_widget(header)

        self.summary = Label(text="Round 1 • 10 players", size_hint_y=None,
                             height=dp(25), color=(0.7, 0.8, 0.9, 1))
        root.add_widget(self.summary)

        self.tabs = TabbedPanel(do_default_tab=False, tab_width=dp(125))
        self.tabs.background_color = (0.06, 0.12, 0.2, 1)
        self.tabs.add_widget(self.make_players_tab())
        self.tabs.add_widget(self.make_locations_tab())
        self.tabs.add_widget(self.make_claims_tab())
        self.tabs.add_widget(self.make_events_tab())
        self.tabs.add_widget(self.make_guide_tab())
        root.add_widget(self.tabs)

        self.refresh()
        return root

    def _update_bg(self, widget, *_):
        self.bg_rect.pos = widget.pos
        self.bg_rect.size = widget.size

    def small_button(self, text, callback, width=None):
        btn = Button(text=text, size_hint_x=None if width else 1,
                     width=width or 0, size_hint_y=None, height=dp(42),
                     background_normal="", background_color=(0.08, 0.35, 0.58, 1),
                     color=(1, 1, 1, 1))
        btn.bind(on_release=lambda *_: callback())
        return btn

    def make_tab(self, title, content):
        tab = TabbedPanelItem(text=title)
        tab.add_widget(content)
        return tab

    def scroll_content(self):
        scroll = ScrollView(do_scroll_x=False)
        content = GridLayout(cols=1, spacing=dp(7), padding=dp(8),
                             size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        scroll.add_widget(content)
        return scroll, content

    def section_label(self, text):
        return Label(text=f"[b]{text}[/b]", markup=True, size_hint_y=None,
                     height=dp(32), color=(0.4, 0.85, 1, 1),
                     halign="left", valign="middle")

    def make_players_tab(self):
        scroll, self.player_list = self.scroll_content()
        self.player_list.add_widget(self.section_label("PLAYERS • 10 SLOTS"))
        self.player_rows_box = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        self.player_rows_box.bind(minimum_height=self.player_rows_box.setter("height"))
        self.player_list.add_widget(self.player_rows_box)
        self.player_list.add_widget(self.small_button("Recalculate scores", self.refresh))
        return self.make_tab("Players", scroll)

    def make_locations_tab(self):
        scroll, box = self.scroll_content()
        box.add_widget(self.section_label("LOG PLAYER LOCATION"))
        self.loc_player = Spinner(text=self.players[0].name, values=self.player_names(),
                                   size_hint_y=None, height=dp(44))
        self.loc_room = Spinner(text="Electrical", values=ROOMS,
                                size_hint_y=None, height=dp(44))
        self.loc_time = self.entry("Time e.g. 0:45")
        self.loc_source = Spinner(text="Observed",
                                  values=["Observed", "Player report", "Camera"],
                                  size_hint_y=None, height=dp(44))
        for w in (self.loc_player, self.loc_room, self.loc_time, self.loc_source):
            box.add_widget(w)
        box.add_widget(self.small_button("Add location", self.add_location))
        box.add_widget(self.section_label("ROUND TIMELINE"))
        self.timeline_label = self.output_label()
        box.add_widget(self.timeline_label)
        nav = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        nav.add_widget(self.small_button("Previous round", lambda: self.change_round(-1)))
        nav.add_widget(self.small_button("Next round", lambda: self.change_round(1)))
        box.add_widget(nav)
        return self.make_tab("Locations", scroll)

    def make_claims_tab(self):
        scroll, box = self.scroll_content()
        box.add_widget(self.section_label("RECORD AN ALIBI / CLAIM"))
        self.claim_player = Spinner(text=self.players[0].name, values=self.player_names(),
                                    size_hint_y=None, height=dp(44))
        self.claim_room = Spinner(text="MedBay", values=ROOMS,
                                  size_hint_y=None, height=dp(44))
        self.claim_time = self.entry("Claim time e.g. 0:45")
        self.claim_detail = self.entry("Claim details")
        self.claim_partner = Spinner(text="(No partner)",
                                     values=["(No partner)"] + self.player_names(),
                                     size_hint_y=None, height=dp(44))
        self.claim_verified = Spinner(text="Unverified",
                                      values=["Unverified", "Verified"],
                                      size_hint_y=None, height=dp(44))
        for w in (self.claim_player, self.claim_room, self.claim_time,
                  self.claim_detail, self.claim_partner, self.claim_verified):
            box.add_widget(w)
        box.add_widget(self.small_button("Add claim", self.add_claim))
        box.add_widget(self.small_button("Run contradiction checks", self.refresh))
        self.claim_output = self.output_label()
        box.add_widget(self.section_label("CLAIMS & EVIDENCE"))
        box.add_widget(self.claim_output)
        return self.make_tab("Alibis", scroll)

    def make_events_tab(self):
        scroll, box = self.scroll_content()
        box.add_widget(self.section_label("LOG A MATCH EVENT"))
        self.event_kind = Spinner(text="Body reported",
            values=["Body reported", "Emergency meeting", "Kill window",
                    "Task witnessed", "Other"], size_hint_y=None, height=dp(44))
        self.event_detail = self.entry("Description / room / time (e.g. Kill window at 0:45)")
        box.add_widget(self.event_kind)
        box.add_widget(self.event_detail)
        box.add_widget(self.small_button("Add event", self.add_event))
        box.add_widget(self.section_label("MANUAL PLAYER FLAG"))
        self.flag_player = Spinner(text=self.players[0].name, values=self.player_names(),
                                   size_hint_y=None, height=dp(44))
        self.flag_kind = Spinner(text="Seen near body", values=list(FLAGS),
                                 size_hint_y=None, height=dp(44))
        box.add_widget(self.flag_player)
        box.add_widget(self.flag_kind)
        box.add_widget(self.small_button("Add flag", self.add_flag))
        box.add_widget(self.section_label("MEETING NOTES"))
        self.notes_input = TextInput(text="", hint_text="Write meeting notes...",
                                     multiline=True, size_hint_y=None, height=dp(150),
                                     background_color=(0.08, 0.12, 0.19, 1),
                                     foreground_color=(1, 1, 1, 1))
        box.add_widget(self.notes_input)
        return self.make_tab("Events", scroll)

    def make_guide_tab(self):
        scroll, box = self.scroll_content()
        guide = (
            "[b]SUSPICION SCORE[/b]\\n"
            "Contradiction: +22 (maximum +44)\\n"
            "Unverified alibi in kill window: +14 (maximum +28)\\n"
            "Suspicious travel timing: +18 (maximum +36)\\n"
            "Manual flags: weighted +6 to +24 (maximum +36)\\n\\n"
            "Scores are heuristic review priorities, not proof or a real probability. "
            "The room graph uses approximate walking times. Vents, map variants, "
            "doors, sabotage, and observation delays can change travel times.\\n\\n"
            "[b]PRIVACY[/b]\\n"
            "This app does not connect to Among Us. Data is stored locally in the "
            "application's private storage."
        )
        label = Label(text=guide, markup=True, size_hint_y=None,
                      halign="left", valign="top", color=(0.85, 0.9, 1, 1))
        label.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1] + dp(30)))
        box.add_widget(label)
        return self.make_tab("Guide", scroll)

    def entry(self, hint):
        return TextInput(hint_text=hint, multiline=False, size_hint_y=None,
                         height=dp(44), background_color=(0.08, 0.12, 0.19, 1),
                         foreground_color=(1, 1, 1, 1), cursor_color=(0.3, 0.9, 1, 1))

    def output_label(self):
        label = Label(text="", size_hint_y=None, halign="left", valign="top",
                      color=(0.84, 0.9, 0.97, 1), markup=True)
        label.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        label.bind(texture_size=lambda inst, val: setattr(inst, "height", max(dp(70), val[1] + dp(12))))
        return label

    def player_names(self):
        return [p.name for p in self.players]

    def player_for(self, name):
        return next((p for p in self.players if p.name == name), None)

    def notify(self, title, message):
        Popup(title=title, content=Label(text=message),
              size_hint=(0.86, None), height=dp(190)).open()

    def add_location(self):
        name, room = self.loc_player.text, self.loc_room.text
        raw = self.loc_time.text.strip()
        sec = to_seconds(raw) if raw else None
        if not self.player_for(name) or room not in ROOMS or (raw and sec is None):
            self.notify("Check location", "Choose a player and room. Time must be seconds or M:SS.")
            return
        self.locations.append({
            "round": self.round_no, "player": name, "room": room,
            "time": raw or "unspecified", "seconds": sec,
            "source": self.loc_source.text, "logged": clock_text()
        })
        self.loc_time.text = ""
        self.refresh()

    def add_claim(self):
        name, room = self.claim_player.text, self.claim_room.text
        raw, detail = self.claim_time.text.strip(), self.claim_detail.text.strip()
        sec = to_seconds(raw) if raw else None
        partner = self.claim_partner.text
        if not self.player_for(name) or room not in ROOMS or not detail or (raw and sec is None):
            self.notify("Check claim", "Choose a player and room, add details, and use a valid time.")
            return
        if partner == name:
            self.notify("Invalid partner", "A player cannot list themselves as their partner.")
            return
        self.claims.append({
            "player": name, "room": room, "time": raw or "unspecified",
            "seconds": sec, "detail": detail,
            "partner": "" if partner == "(No partner)" else partner,
            "verified": self.claim_verified.text == "Verified",
            "round": self.round_no
        })
        self.claim_time.text = ""
        self.claim_detail.text = ""
        self.refresh()

    def add_event(self):
        detail = self.event_detail.text.strip()
        if not detail:
            self.notify("Missing details", "Enter a short event description.")
            return
        self.events.append({
            "kind": self.event_kind.text, "detail": detail,
            "time": clock_text(), "round": self.round_no
        })
        self.event_detail.text = ""
        self.refresh()

    def add_flag(self):
        player = self.player_for(self.flag_player.text)
        if not player:
            return
        player.flags.append(self.flag_kind.text)
        self.events.append({
            "kind": "Manual flag", "detail": f"{player.name}: {self.flag_kind.text}",
            "time": clock_text(), "round": self.round_no
        })
        self.refresh()

    def change_round(self, delta):
        self.round_no = max(1, self.round_no + delta)
        self.refresh()

    def calculate_scores(self):
        result = {p.name: {"score": 0, "reasons": [], "contradictions": 0,
                           "unverified": 0, "movement": 0} for p in self.players}

        # Contradictions: partner's timed claim differs in room within 15 sec.
        seen_pairs = set()
        for claim in self.claims:
            if not claim["partner"] or claim["seconds"] is None:
                continue
            for other in self.claims:
                if (other["player"] != claim["partner"] or other["seconds"] is None
                    or abs(other["seconds"] - claim["seconds"]) > 15
                    or other["room"] == claim["room"]):
                    continue
                key = tuple(sorted((claim["player"], other["player"]))) + (
                    min(claim["seconds"], other["seconds"]), claim["round"])
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                for who in (claim["player"], other["player"]):
                    if who in result:
                        result[who]["contradictions"] += 1
                        result[who]["reasons"].append(
                            f"Partner claim conflict with {other['player'] if who == claim['player'] else claim['player']}."
                        )

        # Kill-window descriptions may include a time marker such as 0:45.
        for event in self.events:
            if event["kind"] != "Kill window":
                continue
            match = re.search(r"(?<!\\d)(\\d{1,2}:\\d{2})(?!\\d)", event["detail"])
            marker = to_seconds(match.group(1)) if match else None
            if marker is None:
                continue
            for claim in self.claims:
                if (claim["seconds"] is not None and not claim["verified"]
                    and abs(claim["seconds"] - marker) <= 20):
                    result[claim["player"]]["unverified"] += 1

        # Approximate movement checks within the same round.
        for player in self.players:
            observations = sorted(
                [x for x in self.locations if x["player"] == player.name and x["seconds"] is not None],
                key=lambda x: (x["round"], x["seconds"])
            )
            for first, second in zip(observations, observations[1:]):
                if first["round"] != second["round"] or second["seconds"] <= first["seconds"]:
                    continue
                required = shortest_time(first["room"], second["room"])
                elapsed = second["seconds"] - first["seconds"]
                if required is not None and elapsed + 3 < required:
                    result[player.name]["movement"] += 1
                    result[player.name]["reasons"].append(
                        f"Movement warning: {first['room']} to {second['room']} in {elapsed}s; estimated route {required}s."
                    )

        for player in self.players:
            item = result[player.name]
            points = min(44, item["contradictions"] * 22)
            points += min(28, item["unverified"] * 14)
            points += min(36, item["movement"] * 18)
            manual = min(36, sum(FLAGS.get(flag, 8) for flag in player.flags))
            points += manual
            if item["contradictions"]:
                item["reasons"].append(f"{item['contradictions']} contradiction signal(s).")
            if item["unverified"]:
                item["reasons"].append(f"{item['unverified']} unverified claim(s) overlap a kill window.")
            item["reasons"].extend("Manual flag: " + flag for flag in player.flags)
            item["score"] = min(100, points)
            if not item["reasons"]:
                item["reasons"].append("No recorded evidence raises the score.")
        return result

    def refresh(self):
        self.score_data = self.calculate_scores()
        if hasattr(self, "player_rows_box"):
            self.player_rows_box.clear_widgets()
            for player in self.players:
                score = self.score_data[player.name]["score"]
                color = COLORS.get(player.color, "#ffffff")
                row = BoxLayout(size_hint_y=None, height=dp(72), spacing=dp(5))
                row.add_widget(Label(
                    text=f"[b]{player.name}[/b]\\n[color={color[1:]}]● {player.color}[/color]  •  {player.status}",
                    markup=True, halign="left"
                ))
                row.add_widget(Label(text=f"[b]{score}%[/b]", markup=True,
                                     size_hint_x=0.22,
                                     color=(0.3, 0.9, 0.65, 1) if score < 25 else
                                           (1, 0.75, 0.25, 1) if score < 55 else
                                           (1, 0.4, 0.5, 1)))
                actions = BoxLayout(orientation="vertical", size_hint_x=0.48, spacing=dp(2))
                status_btn = Button(text=player.status, font_size="11sp",
                                    background_normal="", background_color=(0.16, 0.25, 0.38, 1))
                status_btn.bind(on_release=lambda _, p=player: self.status_popup(p))
                flag_btn = Button(text="Flag", font_size="11sp",
                                  background_normal="", background_color=(0.45, 0.18, 0.12, 1))
                flag_btn.bind(on_release=lambda _, p=player: self.quick_flag(p))
                actions.add_widget(status_btn)
                actions.add_widget(flag_btn)
                row.add_widget(actions)
                self.player_rows_box.add_widget(row)

        if hasattr(self, "summary"):
            alive = sum(p.status == "Alive" for p in self.players)
            self.summary.text = f"Round {self.round_no} • {alive} alive • {len(self.events)} events • {len(self.claims)} claims"
        if hasattr(self, "timeline_label"):
            timeline = []
            for loc in self.locations:
                timeline.append(f"[R{loc['round']}] {loc['player']} → {loc['room']} ({loc['time']}; {loc['source']})")
            for event in self.events:
                timeline.append(f"[R{event['round']}] {event['kind']}: {event['detail']}")
            self.timeline_label.text = "\\n".join(timeline) if timeline else "No match events logged yet."
        if hasattr(self, "claim_output"):
            lines = []
            for claim in self.claims:
                partner = f" • with {claim['partner']}" if claim["partner"] else ""
                verification = "VERIFIED" if claim["verified"] else "UNVERIFIED"
                lines.append(f"{claim['player']} at {claim['room']} [{claim['time']}] — {claim['detail']}{partner} ({verification})")
            lines.append("\\n[b]EVIDENCE BREAKDOWN[/b]")
            for name, data in self.score_data.items():
                if data["score"]:
                    lines.append(f"\\n[b]{name}: {data['score']}%[/b]")
                    lines.extend("• " + reason for reason in data["reasons"])
            self.claim_output.text = "\\n".join(lines) if lines else "No claims recorded."

    def status_popup(self, player):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        spinner = Spinner(text=player.status, values=STATUSES, size_hint_y=None, height=dp(44))
        content.add_widget(Label(text=f"Set status for {player.name}"))
        content.add_widget(spinner)
        popup = Popup(title="Player status", content=content,
                      size_hint=(0.85, None), height=dp(190))
        btn = self.small_button("Apply", lambda: self._apply_status(player, spinner.text, popup))
        content.add_widget(btn)
        popup.open()

    def _apply_status(self, player, status, popup):
        player.status = status
        popup.dismiss()
        self.refresh()

    def quick_flag(self, player):
        flag = "Manual suspicion"
        if flag in player.flags:
            player.flags.remove(flag)
        else:
            player.flags.append(flag)
        self.refresh()

    def session_data(self):
        return {
            "version": 1, "round": self.round_no,
            "players": [p.data() for p in self.players],
            "locations": self.locations, "claims": self.claims,
            "events": self.events,
            "notes": getattr(self, "notes_input", None).text if hasattr(self, "notes_input") else self.notes
        }

    def save_match(self):
        try:
            path = os.path.join(self.user_data_dir, "among_us_match.json")
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self.session_data(), handle, indent=2, ensure_ascii=False)
            self.notify("Match saved", "Saved locally in the app's private storage.")
        except (OSError, TypeError) as exc:
            self.notify("Save failed", str(exc))

    def load_match(self):
        path = os.path.join(self.user_data_dir, "among_us_match.json")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if data.get("version") != 1 or len(data.get("players", [])) != 10:
                raise ValueError("This is not a supported match save.")
            self.players = [
                Player(p["name"], p["color"], p.get("status", "Alive"), p.get("flags", []))
                for p in data["players"]
            ]
            self.locations = data.get("locations", [])
            self.claims = data.get("claims", [])
            self.events = data.get("events", [])
            self.round_no = max(1, int(data.get("round", 1)))
            self.notes = data.get("notes", "")
            if hasattr(self, "notes_input"):
                self.notes_input.text = self.notes
            # Refresh spinner options after replacing player names.
            for widget_name in ("loc_player", "claim_player", "flag_player"):
                widget = getattr(self, widget_name, None)
                if widget:
                    widget.values = self.player_names()
                    widget.text = self.player_names()[0]
            if hasattr(self, "claim_partner"):
                self.claim_partner.values = ["(No partner)"] + self.player_names()
            self.refresh()
            self.notify("Match loaded", "Your saved match was restored.")
        except FileNotFoundError:
            self.notify("No save found", "Save a match first, then load it here.")
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            self.notify("Load failed", str(exc))


if __name__ == "__main__":
    DeductionApp().run()
