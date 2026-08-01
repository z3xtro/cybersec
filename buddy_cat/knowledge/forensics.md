# Forensics & Steganography

> Signals: forensics stego steganography image png jpg wav audio spectrogram pcap wireshark packet capture memory volatility disk carve binwalk exif zsteg steghide lsb hidden metadata zip crack.

## File & data forensics
- `file`, `binwalk -e`, `foremost`, `photorec` — carve embedded/deleted files.
- `strings`, `exiftool`, `xxd` — metadata and hidden tails after EOF markers.
- Check for appended data after image EOF (`FFD9` for JPEG, `IEND` for PNG).
- Archives: try `zip`/`7z` with wordlists; `fcrackzip -D -p wordlist file.zip`.

## Images (stego)
- `zsteg` (PNG/BMP LSB), `steghide extract -sf file.jpg` (often passphrase-protected),
  `stegsolve` (bit planes, channel swaps), `outguess`.
- LSB in RGB channels; look at each bit plane; check alpha channel.
- PNG: `pngcheck -v`; fix wrong width/height in IHDR to reveal hidden content.

## Audio
- `Audacity`/`Sonic Visualiser` spectrogram (flags drawn in the spectrum).
- DTMF tones, Morse in the waveform, SSTV (`qsstv`), slowed/reversed audio.

## Network (pcap)
- `wireshark` / `tshark`; `Follow TCP/HTTP stream`.
- Export objects: `File > Export Objects > HTTP`. Extract files from streams.
- `tshark -r cap.pcap -Y http.request -T fields -e http.host -e http.request.uri`.
- Look for creds in plaintext protocols, DNS exfil, ICMP data, USB keystrokes.

## Memory forensics
- `volatility3` (or vol2): `windows.pslist`, `windows.cmdline`, `windows.filescan`,
  `windows.dumpfiles`, `windows.hashdump`. Identify the profile first.

## Disk
- Mount images read-only; `autopsy`/`sleuthkit` (`fls`, `icat`) for deleted files.

## Tools
binwalk, foremost, exiftool, zsteg, steghide, stegsolve, wireshark/tshark,
volatility3, sleuthkit/autopsy, Audacity, Sonic Visualiser, fcrackzip.
