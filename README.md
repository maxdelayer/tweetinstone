# tweetinstone

Toolset to automate screenshot archival of tweets in their most original/canonical presentation at the time of capture

## Table of Contents

- [Design Intent](#design-intent)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Considerations](#considerations)
- [Known issues](#known-issues)
- [Credit](#credit)

### Design Intent

The goal of this project is to take screenshots and additional metadata from tweets in an automated fashion. This is pretty typical behavior if you want to reference a tweet in some other medium where you can't simply embed (such as editing a video) or where embedding a link is insufficient for full context (such as posting on discord). It is also important for archiving a tweet in case it is deleted, the user is banned/deleted/goes private, or twitter explodes/has an outage which would essentially lose that tweet to time like tears in the rain.

The internet is (for better and worse) ephemeral, so I want to empower those who have tweets that they enjoy to be able to save them. Not just save them as data or a rough screeNshot, but in high resolution as they would be seen (more or less) at the time of reference, with all associated images and video that the tweet contains in its highest possible quality. 

If you are someone who likes to have local copies of tweets for whatever reason, I hope that this tool lets the computer do the work instead of you, giving you more time to do real human things. That's the reason this exists.

*-Max*

### Installation

#### Via PIP

To maximize ease of use, I've published this to PyPI. You can install tweetinstone with
```bash
pip3 install tis
```

#### Manually

This tool was built and tested on WSL, but given it's python it should be highly portable. Presuming you have a working python and pip installation, it should be as simple as installing the requirement packages, setting up Playwright and running the script from the command line.

After cloning this repository or downloading and extracting the release zip, you can run the following from inside the project folder:
```bash
pip3 install -r requirements.txt
```

##### Important Note:

Playwright requires additional setup to install the web browsers it uses. Don't worry, these won't overwrite any settings of your existing web browsers you've installed.
```bash
playwright install
playwright install-deps
``` 

### Usage

On installation via PIP, there are two commands: `tis` and `tis-gui`. Running `tis` will run the command line version and `tis-gui` will default to a GUI for ease of use. The help page that displays when you run `tis` without any command line arguments will list what each argument does, but the simple version is this:

1. Specify a search target (either an individual url or a file containing a list of urls)
2. Run!

The nuance is with the different search modes. If you don't specify a cookie file, tweetinstone can only see the single tweet you link, even if it is a reply or in a thread. If you specify a cookie file, tweetinstone will default to grabbing the tweet specified and any tweets preceding it, and concatenate them together. When you have cookies, you can also attemp the 'thread' search mode which will keep looking for tweets by the first user until they stop, but this is broken right now.

##### Video Capture

If a tweet has a single video, tweetinstone will download it and create a new video that composites the video inside of an image of the tweet using ffmpeg. Multi-video download is not supported right now since it's a huge pain in the ass.

##### Image Capture

Tweetinstone will attempt to download the highest quality version of any images attached to the tweet.

#### Command Line Arguments

##### General Options

| Argument | Shorthand | Effect | Example |
| :---: | :---: | :--- | :--- |
| --help | -h | Display help menu |  |
| --verbose | -v | Displays extra ffmpeg information |  |
| --cookies | -c | Input a cookie file | `./tis.py -c ./cookie.txt https://twitter.com/` |
| --no-cookies | -n | Disregard default cookie file | |
| --version |  | Display version number |  |

##### Input Options

There are two modes of input: urls as command line arguments, and urls inside of a text file.

| Input method | Argument | Shorthand | Input | Example |
| :---: | :---: | :---: | :--- | :--- |
| URL | \[url\] |  | a single URL or multiple, space-separated urls | `./tis.py https://twitter.com/atomicthumbs/status/1649952816268742656` |
| Text file | --input | -i | A text file containing line-separate tweet urls | `./tis.py -i tweets.txt` |

##### Scope Options

There are multiple modes to tweak the output tweetinstone collects. By default, for each tweet that is input, it grabs that tweet and any tweets it is replying to. Each of these tweets will be saved to a subfolder of the .zip archive, and at the root of the archive will be a concatenation of all these tweets into a single image.

##### Important Note:

Due to modern twitter policy, the default capture of replies and the option to capture the thread will **not** work unless user session cookies are imported.

| Argument | Shorthand | Effect |
| :---: | :--- | :--- |
| --only | -o | Only get the singular tweet that's specified in the url |
| --thread | -t | Get each tweet in the user's thread (everything before the tweet and after the tweet by the original user) |

##### Customization Options

These allow you to customize the appearance of the tweets with web browser settings. For localization reasons and such.

| Argument | Shorthand | Effect | Default Value |
| :---: | :--- | :--- | :---: |
| --color |  | Set browser color scheme (`dark` or `light`) | dark |
| --scale | -s | Set DPI scaling factor | 4 |
| --locale | -l | Set browser locale | en-US |
| --timezone |  | Set time zone | America/New_York |

### Configuration

You can import cookies into tweetinstone to allow the script to view twitter as your account. 

The only cookie it cares about is the `auth_token` cookie, a string of characters that is effectively your secret random password that tells the twitter servers that your web browser is 'you'. When you log in, this session token cookie is what lets twitter 'remember' that you are logged in on that web browser. Some behavior such as changing passwords, logging out, or logging out of all sessions, will invalidate the session token and force you to use it again.

##### ***!!!WARNING WARNING WARNING!!!***

Your session token allows tweetinstone to view twitter as your account. This means that if it is acquired by malicious actors or used by other programs, *they* could view twitter as your account and thus could cause problems for your account. It is also unclear if twitter would at some point do a reprisal for using a session token in this way and assume that tweetinstone is malicious.

- *Copy and store your session token cookie at your own risk*
- ***NEVER** reveal your session token in screenshots, video, or text, especially not when attempting to get support for tweetinstone*
- *If you believe your session has been compromised, change your password and use twitter settings to log out of your account on all devices*

#####  ***!!!WARNING WARNING WARNING!!!***

#### Finding Your Auth Token

You can export cookies with browser extensions such as those recommended by [other tools](https://github.com/mikf/gallery-dl#cookies) however since tweetinstone only cares about one specific cookie, the simplest way to view it is to use your browsers developers tools when logged in to twitter.

##### Firefox

In firefox, open the dev tools with `f12` and then click the [storage](https://firefox-source-docs.mozilla.org/devtools-user/storage_inspector/index.html) tab. Click on the cookie with the name 'auth_token'. A window will pop up on the right that has the cookie's data. Right click where it says 'auth_token' and select 'copy'. 

Paste this into a text file. Remove the other text until you just have the value in between the parenthesis. If the file just contains the auth token string, you're good to go!

##### Chrome

TODO

#### ~~Simplified Auth Token Config (NOT FUNCTIONAL)~~

~~For simplicity's sake, since cookies are so key to extended functionality, by default, tweetinstone will look for a file named `auth.txt` in the current directory. If you save your cookie to this filename, you won't need to use `--cookie` option every time.~~

##### Note:

Default cookie file usage can be disabled with the `-n` option

### Considerations
Twitter's behavior has been a bit wonky as of the time of writing. Some changes in Summer 2023 have been problamatic. Because of new policies where only logged in users can see replies to tweets, if you do not have an `auth_token` cookie for tweetinstone to log yourself in, tweetinstone will only be able to grab the single tweet in the url, and may have limited functionality or unexpected behavior.

Changes twitter makes that cause upstream issues in `youtube-dl` may require updating your `youtube-dl` library's version when workarounds have been implemented in `youtube-dl`.

Lastly, any use of tweetinstone carries no obligation of support, regardless of how timely or untimely. This is something I built in my free time because I wanted it to exist so I could use it myself, but that I am allowing the public to use for free. However, if you play nice I do appreciate reports of problems (preferably via github issues) because I have no chance of fixing problems I cannot see.

### Known Issues

In the interest of getting a working build out there and actually semi-finishing a project, tweetinstone has released in an imperfect state. Here is a list of known issues:
 - Thread traversal is broken and won't grab the entire thread
 - Video capture is broken after the latest twitter domain changes on older yt-dlp versions
 - Default cookie support has not been added

### Credit
 - [@atomicthumbs for the idea](https://twitter.com/atomicthumbs/status/1649952816268742656)
 - Playwright for making programmatically interacting with web browsers easy
 - ffmpeg for being awesome (plus the person who made an awesome python wrapper for it)
 - Various helpful posts I've given kudos to in the code where appropriate
