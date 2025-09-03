# ShopeePH Live Replay Downloader

 
A small CLI tool to download Shopee Philippines live replay videos by fetching the replay M3U8, downloading TS segments, and concatenating them into an MP4.

## Requirements

- Python 3.13+

- ffmpeg (must be installed and available on PATH)

## Quick install

Open a terminal and run:

```sh
pip install -r requirements.txt
```

or with `uv`:

```sh
uv sync
```

## Usage

Run the downloader and follow the prompts:

```sh
python download.py
```

or with `uv`:

```sh
uv run download.py
```

You can paste either a full Shopee live replay URL (e.g. `https://live.shopee.ph/...`) or a session ID when prompted. If the replay URL includes a specific record ID the script will download that single recording; otherwise it will fetch all records for the session and download them one-by-one.

## Notes

- The script writes temporary .ts segment files into a `downloads` folder and removes them after creating the final MP4.

- Ensure `ffmpeg` is on your PATH so the script can run the concatenation step.

- Network timeouts and API errors are printed to the console; re-run if a download fails.
