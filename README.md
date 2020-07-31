# Pod Local Sync

This utility allows you to manage a podcast RSS feed locally and spin up a small
server to sync it with podcast applications like macOS' Podcast.app.

I wrote this since in macOS Catalina (10.15), it is no longer possible to
manually add local files to the app.

## How to

Python 3.8 is required.

```bash
pip install podlocalsync
```

`podlocalsync` works in the current directory and will automatically pick up
files.

To start, you need an image for the feed in the current directory:

```console
$ podlocalsync init
Feed title: My Feed
Using image myimage.png.
```

This will create `feed.toml`, which stores the information about the feed.

Next, you can add episodes. `podlocalsync` will look for `*.m4a` and `.mp3`
files. The publication date is also filled in from the file time.

```console
$ podlocalsync add
Episode audio: [episode-1.m4a]:
 [0] episode-1.m4a
 [1] episode-2.mp3
 [2] episode-3.m4a
 >
Episode title: My Episode about Cats
Episode publication date: [Fri, 31 Jul 2020 06:26:31 +0000]
```

If you've added an episode, it will be excluded from the next `add`.

Finally, you can serve the feed locally. This will create or overwrite
`feed.rss` and spin up a server:

```console
$ podlocalsync serve
http://localhost:8000/feed.rss
^C
Keyboard interrupt received, exiting.
```

You can subscribe to this URL in a podcasting application, although the server
isn't intended to be run for a long time, and certainly [don't expose it to the
internet](https://docs.python.org/3/library/http.server.html).

If you want to subscribe from e.g. an iPhone, use your computer's IP address
as the hostname (and make sure the firewall allows connections):

```console
$ podlocalsync serve --host 192.168.1.136
http://192.168.1.136:8000/feed.rss
```

## License

This program is licensed under the GNU General Public License 3.0. For more information, see `LICENSE`.
