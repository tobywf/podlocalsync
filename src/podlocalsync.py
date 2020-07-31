from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from itertools import chain
from pathlib import Path
from uuid import uuid4

import toml
from cleo import Application, Command, option
from lxml import etree
from lxml.builder import ElementMaker

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"


class InitCommand(Command):
    name = "init"
    description = "Set up a new feed."
    help = description

    options = [
        option("title", None, "Feed title", flag=False),
        option("image", None, "Feed image.", flag=False),
    ]

    def handle(self):
        cwd = Path.cwd()
        config_path = cwd / "feed.toml"

        if config_path.exists():
            self.line("<error><comment>feed.toml</> already exists.</>")
            return 1

        title = self.option("title")
        if not title:
            question = self.create_question("Feed title:")
            title = self.ask(question)

        image = self.option("image")
        if not image:
            images = sorted(
                chain(cwd.glob("*.png"), cwd.glob("*.jpg"), cwd.glob("*.jpeg"))
            )
            if not images:
                self.line(
                    "<error>No <comment>*.png</>, <comment>*.jpg</>, or <comment>"
                    "*.jpeg</> files found in the current directory.</>"
                )
                return 1

            if len(images) == 1:
                image = images[0].name
                self.line(f"Using image <comment>{image}</>.")
            else:
                image = self.choice("Feed image:", [image.name for image in images], 0)

        config = {"feed": {"title": title, "image": image}}

        with config_path.open("w", encoding="utf-8") as f:
            toml.dump(config, f)


class AddCommand(Command):
    name = "add"
    description = "Add a new episode to the feed."
    help = description

    options = [
        option("title", None, "Episode title", flag=False),
        option("audio", None, "Episode audio.", flag=False),
        option("pubdate", None, "Episode publication date.", flag=False),
    ]

    def handle(self):
        cwd = Path.cwd()
        config_path = cwd / "feed.toml"

        try:
            with config_path.open("r", encoding="utf-8") as f:
                config = toml.load(f)
        except FileNotFoundError:
            self.line(
                "<error><comment>feed.toml</> not found. Have you created a feed?</>"
            )
            return 1

        episodes = config.get("episodes", [])

        audio = self.option("audio")
        if not audio:
            audios = sorted(chain(cwd.glob("*.m4a"), cwd.glob("*.mp3")))
            if not audios:
                self.line(
                    "<error>No <comment>*.m4a</> or <comment>*.mp3</> files"
                    " found in the current directory.</>"
                )
                return 1

            used = {episode["audio"] for episode in episodes}
            choices = [audio.name for audio in audios if audio.name not in used]

            if not choices:
                self.line(
                    "<error>No unused <comment>*.m4a</> or <comment>*.mp3</>"
                    " files found in the current directory.</>"
                )
                return 1

            if len(choices) == 1:
                audio = choices[0]
                self.line(f"Using audio <comment>{audio}</>.")
            else:
                audio = self.choice("Episode audio:", choices, 0)

        stat = (Path.cwd() / audio).stat()

        title = self.option("title")
        if not title:
            question = self.create_question("Episode title:")
            title = self.ask(question)

        pubdate = self.option("pubdate")
        if not pubdate:
            timestamp = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
            pubdate = timestamp.strftime("%a, %d %b %Y %H:%M:%S +0000")
            question = self.create_question(
                f"Episode publication date: [<comment>{pubdate}</>]", default=pubdate
            )
            pubdate = self.ask(question)

        episodes.append(
            {
                "title": title,
                "audio": audio,
                "guid": str(uuid4()),
                "length": str(stat.st_size),
                "type": "audio/mpeg" if audio.endswith(".mp3") else "audio/x-m4a",
                "pubdate": pubdate,
            }
        )

        config["episodes"] = episodes

        with config_path.open("w", encoding="utf-8") as f:
            toml.dump(config, f)


class ServeCommand(Command):
    name = "serve"
    description = "Serve the feed locally."
    help = description

    options = [
        option("port", None, "Specify alternate port [default: 8000]", flag=False),
        option("host", None, "Hostname or IP address [default: localhost]", flag=False),
    ]

    def handle(self):
        port = self.option("port")
        if not port:
            port = 8000
        else:
            port = int(port)

        host = self.option("host")
        if not host:
            host = "localhost"

        cwd = Path.cwd()
        config_path = cwd / "feed.toml"

        try:
            with config_path.open("r", encoding="utf-8") as f:
                config = toml.load(f)
        except FileNotFoundError:
            self.line(
                "<error><comment>feed.toml</> not found. Have you created a feed?</>"
            )
            return 1

        url = f"http://{host}:{port}"
        self.line(f"{url}/feed.rss")

        self.make_feed(config, url)

        server_address = ("", port)
        with ThreadingHTTPServer(server_address, SimpleHTTPRequestHandler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                self.line("\nKeyboard interrupt received, exiting.")
                return 0

    def make_feed(self, config, url):
        E = ElementMaker(namespace=None, nsmap={"itunes": ITUNES_NS})
        A = ElementMaker(namespace=ITUNES_NS, nsmap={"itunes": ITUNES_NS})

        feed_image = config["feed"]["image"]

        root = E.rss(
            E.channel(
                E.title(config["feed"]["title"]),
                E.description("---"),
                A.image(href=f"{url}/{feed_image}"),
                E.language("en-US"),
                A.explicit("yes"),
                E.link(url),
                *[
                    E.item(
                        A.episode(str(i)),
                        E.title(episode["title"]),
                        E.enclosure(
                            url=f"{url}/{episode['audio']}",
                            length=episode["length"],
                            type=episode["type"],
                        ),
                        E.guid(episode["guid"], isPermaLink="false"),
                        E.pubDate(episode["pubdate"]),
                        A.explicit("yes"),
                    )
                    for i, episode in enumerate(config["episodes"], 1)
                ],
            ),
            version="2.0",
        )

        with open("feed.rss", "wb") as f:
            f.write(
                etree.tostring(
                    root,
                    xml_declaration=True,
                    encoding="UTF-8",
                    method="xml",
                    pretty_print=True,
                )
            )


def main():
    app = Application(name="podlocalsync")
    app.add(InitCommand())
    app.add(AddCommand())
    app.add(ServeCommand())
    raise SystemExit(app.run())
