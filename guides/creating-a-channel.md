# Creating a channel

This guide takes a programmer who has never heard of teletext from nothing to a published channel. You will write pages by hand, put them on a web host, then write a program that serves live pages, in TypeScript and in Python. It takes you through each step. For depth, read [`servers.md`](servers.md) on the server and the kits, and [`teletext-reference.md`](teletext-reference.md) on everything a page can do.

The examples were run for this guide on a local machine, and the output is what the tools printed, with the local ports written as `8000` and `8090`. Three kinds of command were not run, and the guide marks them: release builds, anything on a public host or behind TLS, and anything in the NeoTeletext browser. It was checked on 1 and 2 November 2026 against these commits:

| What | Commit or version |
|---|---|
| `neottx`, from `neoteletext-engine` | `fecedf4` |
| `teletext-server`, from `neoteletext-app-server` | `cce8d80` |
| TypeScript kit | 6.0.0 |
| UI library | 12.0.0 |
| Python kit, in `neoteletext-server-channels` | `7a2f3e5` |

What a viewer sees was checked with `neottx view`, the terminal receiver. Where the browser matters, the guide says what its code does. Section 19 lists what is not built yet.

## 1. What you are making

Teletext was the text service of analogue television. A broadcaster sent a set of numbered pages round and round in the spare lines of the picture, and a television caught the page you asked for by number. The pages were 40 characters by 25 rows, in eight colours, with blocky graphics made of characters.

NeoTeletext keeps the pages and replaces the broadcast. A **channel** is a teletext service on the web. A **receiver** opens it: the NeoTeletext browser, or the `neottx` command. There are two kinds of channel.

| | Static channel | Live channel |
|---|---|---|
| What it is | A folder of files on any web host | A program behind the Rust server |
| Pages | Files you write or generate | Whatever your program draws, for each viewer if it likes |
| Changes | When you upload new files | The moment your program says so |
| Takes the viewer's keys | No | Yes |
| Needs | Any host that serves files | A machine that runs the server and your program |

Start with a static channel even if you want a live one. The page is the same in both, and it is quicker to learn with a file.

The words used in this guide:

| Word | Meaning |
|---|---|
| Page | One screen, with a number such as `100` |
| Sub-page | One of several screens that share a page number |
| Row | A line of a page, 0 to 24 |
| Packet | The 42 bytes that carry one row. You will rarely see one |
| TTI | The text file format pages are written in |
| T42 | The binary format of packets, 42 bytes each |
| Fastext | The four coloured keys that lead to other pages |
| Selection | The page or sub-page a connection is showing |

## 2. Get the tools

**`neottx`** is the command-line receiver and page tool. Every section uses it. Build it from `neoteletext-engine`, with the Rust the repository pins:

```
cd neoteletext-engine
cargo build --release -p neoteletext-cli
```

The program is `target/release/neottx`. Put it on your path. On macOS it prints a note on standard error that its sandbox is not built there; the output below leaves that note out.

**For a live channel you also need:**

- **`teletext-server`**, from `neoteletext-app-server`: `cargo build --release -p teletext-native`. The program is `target/release/teletext-server`.
- **For TypeScript,** Node 22.18 or later. It runs `.ts` files directly, so there is no build step.
- **For Python,** Python 3.13 or later and `uv`.

## 3. What a page is

A page is a grid of 40 columns by 25 rows. Each cell holds one 7-bit code. There are 8 colours, and no fonts or sizes to choose beyond double height. Pages are drawn in Noto Teletext, the one font, and neither a page nor a channel can name another.

**A cell is either a character or a control code.** A control code changes the colour or the style for the rest of the row, and it takes up a cell, which shows as a space. So a colour change costs a column, and a row is at most 39 characters if it starts with a colour. Every row starts white on black.

**The rows have jobs.**

| Row | What it is |
|---|---|
| 0 | The header. Columns 0 to 7 are the receiver's. Columns 8 to 39 are yours |
| 1 to 23 | Your page |
| 24 | The prompts for the coloured keys |

**Row 0, columns 0 to 7, belong to the receiver.** Nothing a page sends can write there. The receiver shows the page number and its security marks in them, so a page can never forge them. `P100` is page 100. `P1--` is a number being typed. `P100/02` is a sub-page's place. A red `100 !` means the page came over plain `http`, and `LEAVE?` means a link is about to leave the channel. Text you put in those eight columns is thrown away, so start your header text at column 8.

**Page numbers are three hexadecimal digits**, `100` to `8FF`. The first digit is the **magazine**, 1 to 8, which is only a way of grouping pages. A viewer types digits, so the 800 pages from `100` to `899` can be typed. A page such as `1A0` can be reached only by a link. Do not use `mFD`, `mFE` or `mFF` in any magazine, or `1BE` or `1F0`: the standard reserves them. A channel opens at page 100 unless it says otherwise.

**A page can have sub-pages:** several screens under one number, up to 8,190. Each has a four-digit hexadecimal sub-code, `0000` to `3F7E`. `3F7F` means "no particular sub-page". A page with one screen normally has sub-code `0000`. On television sub-pages rotated by themselves. In NeoTeletext they do not on a live channel, where a sub-page changes only when the viewer or the program changes it.

## 4. A static channel in five minutes

Make a folder and one page. A page file is named by its page number, with capital letters for any hexadecimal digits.

```sh
mkdir news
cd news
cat > 100.tti <<'EOF'
PN,10000
SC,0000
PS,8000
OL,0,        EXAMPLE NEWS
OL,1,Hello, teletext
OL,3,This is page 100.
EOF
```

Look at it:

```sh
neottx text 100.tti 100
```

```text
P100    EXAMPLE NEWS
Hello, teletext

This is page 100.
```

The rest of the output is blank rows. Put it on a web server. Any server will do, so for now use Python's, from the folder above:

```sh
cd ..
python3 -m http.server 8000
```

In another terminal, open it as a receiver does. `--allow-local` is needed because receivers refuse addresses on the local network unless told otherwise.

```sh
neottx probe http://127.0.0.1:8000/news/ --allow-local 127.0.0.1
```

```text
channel     http://127.0.0.1:8000/news/
entry file  read: "127.0.0.1/news"
initial     page 100
protocol    no push connection: a static channel, read by its files
selection   100: a page in 9 ms
result      no fault
```

That folder is a channel. The address must end in `/`. `probe` waits 10 seconds for a live connection before it says a channel is static, so give it a moment.

To look at it properly, in a terminal:

```
neottx view http://127.0.0.1:8000/news/ --allow-local 127.0.0.1
```

Everything else is optional. The rest of this part makes the page worth reading.

## 5. Writing a page in TTI

Leave the web server running, and work in the `news` folder from here to section 11.

```sh
cd news
```

A TTI file is plain text, one command a line: two letters, a comma, then the arguments. Lines end in LF or CR LF.

| Line | What it does |
|---|---|
| `PN,mppss` | Starts a page or sub-page. `mpp` is the page number. `ss` is a decimal count that only numbers sub-pages in the file |
| `SC,ssss` | The sub-code, four hexadecimal digits. Without it the sub-code is 0000 |
| `PS,xxxx` | Page status, hexadecimal. Use `8000`, and section 7 says how it picks a language |
| `DE,text` | A description, which is the page's title. Before the first `PN` it applies to the whole file |
| `OL,n,text` | Row `n` |
| `FL,r,g,y,c,5,i` | The Fastext links, section 8 |
| `LN`, `LK`, `LT` | Links, section 8 |
| `RE,x` | The character set group, section 7 |
| `LG,level,text` | A log line for you, not the viewer. `level` is `E`, `W` or `I`. `neottx list FILE -v` prints it |
| `CK,considered,name` | Silences one `neottx check` warning on this page. `name` is `page-number-not-shown`, `no-other-route` or `hidden-content` |

Only `PN` and `OL` are needed: `PN,10100` and `OL,1,Hello` make a whole page. A row need not be 40 characters long, as the reader fills the rest with spaces. Keep every row within 40 codes: the reader cuts a longer one.

Each byte of `OL` text is one cell. Most characters are themselves, but a few ASCII codes show something else in the English set: `#` shows `£`, `_` shows `#`, `[` shows `←`, `]` shows `→`, `^` shows `↑`, `\` shows `½`, `` ` `` shows `—`, `{` shows `¼`, `|` shows `‖`, `}` shows `¾` and `~` shows `÷`.

### Control codes

A control code in `OL` text is the escape byte, 0x1B, followed by a letter: the code plus 0x40. A real escape byte is awkward to type, so set one in a shell variable and write pages in an unquoted here-document. In one, `$`, a backtick and `\` in your text need a backslash.

```sh
E=$(printf '\033')
```

| Write | Code | Effect |
|---|---|---|
| `${E}A` to `${E}G` | 0x01 to 0x07 | Text in red, green, yellow, blue, magenta, cyan, white |
| `${E}H` / `${E}I` | 0x08, 0x09 | Flash on / off |
| `${E}L` / `${E}M` | 0x0C, 0x0D | Normal height / double height |
| `${E}Q` to `${E}W` | 0x11 to 0x17 | Mosaics in red, green, yellow, blue, magenta, cyan, white |
| `${E}X` | 0x18 | Conceal, until the viewer reveals it |
| `${E}Y` / `${E}Z` | 0x19, 0x1A | Contiguous / separated mosaics |
| `${E}\\` | 0x1C | Black background. The here-document needs the second backslash |
| `${E}]` | 0x1D | New background: the current colour becomes the background |
| `${E}^` / `${E}_` | 0x1E, 0x1F | Hold / release mosaics |

`${E}@` and `${E}P` are black text and black mosaics. Double width and double size, `${E}N` and `${E}O`, are Level 2.5 codes. Reference section 3 has them all, with boxes.

A background takes two cells: the colour, then `${E}]`. After that you give the text its own colour:

```sh
cat > 100.tti <<EOF
DE,Front page
PN,10000
SC,0000
PS,8000
OL,0,        EXAMPLE NEWS
OL,1,${E}D${E}]${E}C${E}M Example News
OL,4,${E}AHeadlines ${E}G101
OL,5,${E}BSport     ${E}G102
OL,6,${E}FPictures  ${E}G300
OL,8,${E}C${E}HFlashing yellow${E}I steady now
OL,10,${E}T${E}]${E}GWhite on blue, all the way across
OL,12,${E}R${E}?${E}?${E}?${E}?${E}?${E}? ${E}Ggreen blocks
LN,R,101,Headlines
LN,G,102,Sport
LN,Y,300,Pictures
LN,I,100,
EOF
```

**Double height** covers the row below, which is not shown, so leave it empty. That is why there is no `OL,2`.

### Mosaics

After a mosaic colour, each cell is a block of six **sixels**, two across and three down. A code is 0x20 plus the bits of the sixels that are on:

| | Left | Right |
|---|---|---|
| Top | 0x01 | 0x02 |
| Middle | 0x04 | 0x08 |
| Bottom | 0x10 | 0x40 |

`#` (0x23) is the top two. `,` (0x2C) is the middle two. `p` (0x70) is the bottom two. `5` (0x35) is the left column, and `j` (0x6A) the right. A full block is 0x7F, which the escape form writes as `${E}?`. Capital letters, 0x40 to 0x5F, stay letters in mosaic mode.

Text after mosaics needs a text colour, or it comes out as blocks.

```sh
cat > 300.tti <<EOF
DE,Pictures
PN,30000
SC,0000
PS,8000
OL,0,        EXAMPLE NEWS
OL,1,${E}CMosaics
OL,3,${E}V${E}Y7#k${E}Z7#k${E}G contiguous, then separated
OL,5,${E}Q${E}?${E}R${E}?${E}S${E}?${E}T${E}?${E}U${E}?${E}V${E}?${E}W${E}?${E}G the seven colours
OL,7,${E}C${E}XThe answer is 42${E}G press reveal
EOF
```

To see a page as a picture, not as text:

```sh
neottx render 300.tti 300 -o 300.png --scale 2
```

`neottx qr TEXT --page PAGE OUT.tti` writes a QR code as mosaics. The engine's `scripts/image-to-teletext.py` turns a picture into a page.

### Sub-pages

Put each sub-page in the one file, each with its own `PN` and `SC`. Give every one an `SC`: without it they all share sub-code 0000, and the last replaces the others.

```sh
cat > 102.tti <<EOF
DE,Sport
PN,10201
SC,0001
PS,8000
OL,0,        EXAMPLE NEWS
OL,1,${E}CSport, page 1 of 3
OL,3,Football
PN,10202
SC,0002
PS,8000
OL,0,        EXAMPLE NEWS
OL,1,${E}CSport, page 2 of 3
OL,3,Cricket
PN,10203
SC,0003
PS,8000
OL,0,        EXAMPLE NEWS
OL,1,${E}CSport, page 3 of 3
OL,3,Tennis
EOF
neottx list 102.tti | head -1
neottx text 102.tti 102/0002 | head -4
```

```text
102  sub-pages   3  receptions     3  errors     0  [0001 0002 0003]
P102    EXAMPLE NEWS
 Sport, page 2 of 3

Cricket
```

Sub-codes are hexadecimal, but the code of practice numbers sub-pages in decimal, so use `0001` to `0079`, skipping `000A`, in ascending order. `neottx view` steps through them with Left and Right. In the runs for this guide it opened such a page at the file's last sub-page, and Right went on to the first.

## 6. Writing a page with `neottx write-text`

`neottx write-text` turns a UTF-8 text file into a page. It breaks lines at 40 columns, at spaces where it can, and chooses every code for you. You choose the set.

```sh
cat > bonjour.txt <<'EOF'
Bonjour à tous
Ça coûte 5 €, déjà vu
EOF
neottx write-text --set french --page 200 bonjour.txt 200.tti
neottx text 200.tti 200 | head -3
```

```text
200.tti: 2 rows, 3 X/26 triplets
P200
Bonjour à tous
Ça coûte 5 €, déjà vu
```

The first line is on standard error. It fills rows 1 to 23 and leaves row 0 and row 24 for you, so a file of more than 23 rows is refused. A character the set cannot write is refused, naming it. Nothing is dropped or replaced silently:

```text
neottx: bad.txt: line 1: the set has no 'П' (U+041F)
```

The command's help lists only some sets. The whole list is in section 7. It takes no colours: for those, edit the `OL` lines it wrote.

## 7. Languages and character sets

A G0 set is the 96 characters a page's rows can show. Each language has one. A page says which by a **designation**, a seven-bit number made of a four-bit **group** and a three-bit **option**, in EN 300 706 Table 32. NeoTeletext adds its own groups, in values the standard reserves. Pages in those sets are unreadable on any other teletext decoder.

The numbers travel two ways:

- **The option alone,** in the header: control bits C12 to C14. This is all that very old sets used. The receiver has to supply the group, from its own region setting.
- **The whole designation,** in **packet X/28/0**, which a TTI file writes as an `OL,28` line. Use this every time.

`write-text` writes both. You will see a line like this in its output, here as `cat -v` prints it. It is packed binary, and is not for writing by hand:

```text
OL,28,@@H|gpCu_@|w^?KpZA`UB_wLs_w}w^?w]^?_^?}_wM@@
```

**By hand, use `RE` and `PS`.** `RE` gives the group, and `PS` the option. A page with `RE` needs no `OL,28`, because the reader builds X/28/0 from those two lines. The row text is then the set's own codes, which is why this Russian page reads as Latin letters in the file:

```sh
cat > 201.tti <<EOF
DE,By hand in Russian
PN,20100
SC,0000
PS,8080
RE,4
OL,1,Priwet, mir
EOF
neottx text 201.tti 201 | sed -n 2p
```

```text
Привет, мир
```

For sets in group 0, where the page's codes are mostly ASCII, `PS` alone does it: `PS,8200` with `OL,1,Gr}~e aus Berlin` is German, `Grüße aus Berlin`. `write-text` is easier for anything else, and is the only sensible way for Arabic, Hebrew, Thai and Lao, which it lays out for you. Arabic and Hebrew are written in visual order, right to left, and Thai and Lao put their marks on rows of their own.

This table is `crates/neoteletext-app/src/write_text/sets.rs` in the engine. For every row, a page written by hand with this `RE` and `PS` was drawn the same as `write-text`'s.

| `--set` | Group | Option | `RE` | `PS` |
|---|---|---|---|---|
| `english` | 0000 | 000 | `0` | `8000` |
| `german` | 0000 | 001 | `0` | `8200` |
| `swedish-finnish-hungarian` | 0000 | 010 | `0` | `8100` |
| `italian` | 0000 | 011 | `0` | `8300` |
| `french` | 0000 | 100 | `0` | `8080` |
| `portuguese-spanish` | 0000 | 101 | `0` | `8280` |
| `czech-slovak` | 0000 | 110 | `0` | `8180` |
| `polish` | 0001 | 000 | `1` | `8000` |
| `turkish` | 0010 | 110 | `2` | `8180` |
| `serbian-croatian-slovenian` | 0011 | 101 | `3` | `8280` |
| `romanian` | 0011 | 111 | `3` | `8380` |
| `estonian` | 0100 | 010 | `4` | `8100` |
| `lettish-lithuanian` | 0100 | 011 | `4` | `8300` |
| `cyrillic-serbian-croatian` | 0100 | 000 | `4` | `8000` |
| `russian-bulgarian` | 0100 | 100 | `4` | `8080` |
| `cyrillic-ukrainian` | 0100 | 101 | `4` | `8280` |
| `greek` | 0110 | 111 | `6` | `8380` |
| `hebrew` | 1010 | 101 | `A` | `8280` |
| `hausa-fula` | 0101 | 000 | `5` | `8000` |
| `west-african` | 0101 | 001 | `5` | `8200` |
| `ewe` | 0101 | 010 | `5` | `8100` |
| `kabyle-tamazight` | 0101 | 011 | `5` | `8300` |
| `azerbaijani` | 0101 | 100 | `5` | `8080` |
| `kanuri-mossi` | 0101 | 101 | `5` | `8280` |
| `yoruba-igbo` | 0101 | 110 | `5` | `8180` |
| `vietnamese` | 0101 | 111 | `5` | `8380` |
| `ukrainian` | 0111 | 000 | `7` | `8000` |
| `belarusian` | 0111 | 001 | `7` | `8200` |
| `macedonian` | 0111 | 010 | `7` | `8100` |
| `serbian` | 0111 | 011 | `7` | `8300` |
| `kyrgyz-mongolian` | 0111 | 101 | `7` | `8280` |
| `tatar` | 0111 | 110 | `7` | `8180` |
| `tajik` | 0111 | 111 | `7` | `8380` |
| `georgian` | 1011 | 000 | `B` | `8000` |
| `armenian` | 1011 | 001 | `B` | `8200` |
| `tifinagh` | 1011 | 010 | `B` | `8100` |
| `persian` | 1001 | 000 | `9` | `8000` |
| `urdu` | 1001 | 001 | `9` | `8200` |
| `pashto` | 1001 | 010 | `9` | `8100` |
| `sindhi` | 1001 | 011 | `9` | `8300` |
| `sorani` | 1001 | 100 | `9` | `8080` |
| `uyghur` | 1001 | 101 | `9` | `8280` |
| `balochi` | 1001 | 110 | `9` | `8180` |
| `arabic` | 1001 | 111 | `9` | `8380` |
| `thai` | 1100 | 010 | `C` | `8100` |
| `lao` | 1100 | 100 | `C` | `8080` |

The `PS` value is 0x8000 with C12 (0x0080), C13 (0x0100) and C14 (0x0200) set from the option, whose bits are C12, C13 and C14 in that order. Sets in the groups NeoTeletext added have Latin English as a second set, which row text reaches with the code 0x1B. `write-text` does this for you when a line mixes the two. In the sets that place a letter's marks by packet X/26, a page has room for about 16 packets of them, so a very dense page of Vietnamese can be refused. `write-text` says so.

**A channel cannot choose a font.** Every page is drawn in Noto Teletext. A `TF` line is an error in `neottx check`, and a `font` member refuses `channel.ttx`. A character the font lacks is drawn as a hollow box. A viewer can load another font in their own receiver, and that does not change what the page says.

## 8. Links and Fastext

Row 24 and the coloured keys are how people move around. There are two ways to write them.

**`LN` lines are the better way.** The receiver draws row 24 for you from the labels. `key` is `R`, `G`, `Y`, `C` for the four colours, or `I` for the Index key, which has no label. A label is at most 9 characters, or 8 for a link that leaves the channel.

```
LN,R,101,Headlines
LN,G,102,Sport
LN,Y,300,Pictures
LN,I,100,
```

**`FL` is the older way.** It gives six page numbers, red, green, yellow, cyan, a fifth link, and Index, with `8FF` for none. It draws nothing, so you write the prompts yourself in row 24:

```sh
cat > 101.tti <<EOF
DE,Headlines
PN,10100
SC,0000
PS,8000
OL,0,        EXAMPLE NEWS
OL,1,${E}CHeadlines
OL,3,Teletext returns to the web.
OL,5,${E}F100${E}G Front page
FL,100,102,300,8FF,8FF,100
OL,24,${E}A Front ${E}B Sport ${E}C Pictures
EOF
```

When a page has both, `LN` wins. Do not put text in row 24 of a page with `LN` lines: it is hidden, and `neottx check` warns you.

A link's **target** has one of these forms:

| Target | Leads to |
|---|---|
| `102` or `102:0002` | A page or sub-page of this channel |
| `news:101` or `news:101:0002` | A page of a channel named in `channel.ttx`'s `services` |
| `https://example.org/other/` | Another channel's folder, or a page file in one |
| `web:https://example.org/story` | A web page, for the receiver to open outside teletext |

Two more lines link the page's own content. A page may have eight of each:

| Line | Meaning |
|---|---|
| `LK,150,news:102` | Typing 150 on this page, or choosing the number printed on it, follows the link. The number should appear on the page. Never `web:` |
| `LT,2,0,8,news:300` | Row 2, from column 0, for 8 characters, is a link. Rows 1 to 23 |

`neottx view` follows `LN` and `FL` links. It did not follow an `LK` line when the number was typed, inside a channel or out of one, and it did not follow an alias. The browser's code handles both, and that was not run.

Keep the page number of every link visible in the page's text, such as "Sport 102". Without it, a page has no way to tell a viewer on a plain receiver where to go, and `neottx check` warns. A link that leaves the channel makes the receiver ask first: `neottx view` shows `LEAVE?` and wants the same key again.

## 9. The channel's own files

### `channel.ttx`

The channel's entry file: its settings, as JSON, whatever the extension says. It is optional, and with no such file a channel takes the defaults. The name is for now, and is expected to change.

```sh
cat > channel.ttx <<'EOF'
{
  "name": "Example News",
  "initial_page": "100",
  "refresh": 60
}
EOF
```

| Member | Holds | Default |
|---|---|---|
| `name` | The channel's name, at most 64 bytes | Its host and folder |
| `initial_page` | The page it opens at, three hexadecimal digits | `"100"` |
| `refresh` | Seconds, 5 to 86,400: how often the page on screen is fetched again | Never |
| `services` | Linked channels, for `name:mpp` targets. At most 16 | None |
| `aliases` | At most 16 page numbers that lead elsewhere on every page | None |
| `region` | The default character set group, 0 to 15 | The receiver's |
| `push` | An object that makes the channel live, section 12 | Not live |

The reader is strict. **An unknown or repeated member refuses the whole file, and the channel does not open.** So does a value of the wrong form. `neottx probe` says why:

```text
said        DescriptorRejected(Unknown)
```

`services` and `aliases` look like this. A `name` is letters, digits and hyphens, at most 32 bytes. A `channel` is a folder's address, ending in `/`. An `https` channel may not name a plain `http` one.

```json
{
  "name": "My portal",
  "services": [
    { "name": "news", "display_name": "Example News", "channel": "https://example.org/news/" }
  ],
  "aliases": { "888": "news:101" }
}
```

`region` gives the group of a page that names none, so a channel in one language need not repeat `RE` on every page. `neottx --region` stands above it. `presentation`, which [DOC-2037](../PROTOCOL.html#DOC-2037) describes, is not built: the reader refuses it as an unknown member.

### `contents.txt`

The channel's table of contents, for the browser's contents view. `neottx contents` writes it from a folder of page files. A page's title is its `DE` line, or else its first row with text. Redirect it to the file, then edit it if you like:

```sh
neottx contents . > contents.txt
cat contents.txt
```

```text
s	Front page
p	100	Front page	2026-11-01
p	101	Headlines	2026-11-01
p	102	Sport	2026-11-01
s	Bonjour tous
p	200	Bonjour tous	2026-11-01
p	201	By hand in Russian	2026-11-01
s	Pictures
p	300	Pictures	2026-11-01
```

Fields are separated by one tab. `s` starts a section, `p` lists a page with a title and an optional date, and `x` lists another channel, as `x`, a target and a title. The tool starts a section at each magazine and names it after the magazine's first page, so `Bonjour tous` above needs editing. Titles are printable ASCII: the `à` of `Bonjour à tous` is gone, so give such a page a `DE` line. Lines starting `#` are comments. The date is the day you ran the tool. `neottx` itself never reads this file: only the browser does, when the contents are shown, and that was not run. The limit is 65,536 bytes and 1,000 lines.

### `index.t42`, to open faster

A reader asks for `index.t42` first, and a 404 is fine. If it exists, it holds pages as T42, so a channel opens with one request and pages appear at once. Make it from your pages:

```sh
mkdir -p ../built
cp channel.ttx ../built/
for page in 100 101 300; do
  neottx convert $page.tti --to t42 -o $page.t42
done
cat 100.t42 101.t42 300.t42 > ../built/index.t42
rm 100.t42 101.t42 300.t42
```

A folder with `channel.ttx` and `index.t42` and nothing else is a whole channel: `neottx probe` found pages 100, 101 and 300 in it with no other request. The limit is 262,144 bytes. Only a page's first sub-page belongs in it if the page has separate sub-page files.

### Pages as T42, and sub-pages as separate files

A page file may be `NNN.t42` in place of `NNN.tti`. A reader tries `.tti` first, then `.t42`. `neottx convert` makes one.

A very large page can keep its sub-pages in a folder named for the page: `602/0101.t42` or `602/0101.tti` for sub-page 0101, the same path as its address `602/0101`. `602.t42` then holds the first sub-page, and `602/0.sub`, `602/1.sub` and so on list them, 64 to a file. A T42 sub-page file is at most 3,108 bytes. [DOC-2038](../PROTOCOL.html#DOC-2038) gives the format of the lists.

Nothing writes these files for you yet: there is no build command (TODO-1224), and the lists hold a validator for each sub-page and a version for the page. `neottx` opens a sub-page you name or key from its file, and steps with Left and Right only through the sub-pages it already holds. The browser reads these files once it takes the engine that writes them. Keep sub-pages in one `NNN.tti` unless the page passes the 256 KiB a page file may be.

## 10. Checking a channel

Each tool answers one question.

| Command | Question |
|---|---|
| `neottx check *.tti` | Are these pages well made? Exit status 4 on an error |
| `neottx list FILE -v` | What did the reader make of this file, line by line? |
| `neottx text FILE PAGE` | What does the page say? `all` for every page |
| `neottx render FILE PAGE -o OUT.png` | What does it look like? |
| `neottx view ADDRESS` | What is it like to use? |
| `neottx probe ADDRESS` | Does the channel answer as a receiver expects? Exit status 0 means no fault |

`check` finds problems with links:

```sh
mkdir -p ../bad
cat > ../bad/100.tti <<'EOF'
PN,10000
OL,1,Nothing here says where to go
LN,R,101,A label far too long
LN,G,weather:400,Weather
LN,G,102,Sport
LK,500,300
TF,somefont
EOF
neottx check ../bad/100.tti
```

```text
../bad/100.tti:5: page 100 sub-page 0: error: TooManyLinks
../bad/100.tti:7: page 100 sub-page 0: error: WithdrawnCommand
../bad/100.tti:3: page 100 sub-page 0: error: LabelTooLong
../bad/100.tti:3: page 100 sub-page 0: warning: Warning(PageNumberNotShown)
../bad/100.tti:4: page 100 sub-page 0: warning: Warning(NoOtherRoute)
../bad/100.tti:5: page 100 sub-page 0: warning: Warning(PageNumberNotShown)
../bad/100.tti:6: page 100 sub-page 0: warning: Warning(PageNumberNotShown)
neottx: 3 error(s)
```

`check` looks at links and at rows longer than the page, and not much else. A row of 50 characters is an error on its line. It passes a line it does not know and an `OL` for a row that does not exist. For those use `list -v`, which reports them as diagnostics and prints your `LG` lines. `check --descriptor channel.ttx` also checks that a link to another service names one the file lists.

`probe` opens a channel and makes each selection you name, then reports how it ended. Use capitals in page numbers. On a live channel it also asks for page `8FC`, to see a page refused.

```sh
neottx probe http://127.0.0.1:8000/news/ --allow-local 127.0.0.1 --select 102 --select 102/0002 --select 300
```

```text
channel     http://127.0.0.1:8000/news/
entry file  read: "Example News"
initial     page 100
protocol    no push connection: a static channel, read by its files
selection   100: a page in 580 ms
selection   102: a page in 296 ms
selection   102/0002: a page in 0 ms
selection   300: a page in 586 ms
result      no fault
```

On a static channel a page that is missing ends the probe with a fault, because nothing tells it the page is not coming: `selection 777: no page and no DENIED within 10 s`, exit status 3. A file whose `PN` disagrees with its name gives the same result, because a page file fills only the page asked for. That is the fault to look for when a page will not appear.

`neottx view` keys: digits for a page number, `r` `g` `y` `c` or F1 to F4 for the coloured keys, `i` for Index, Left and Right for sub-pages, Up and Down for the next and previous page, `?` to reveal concealed text, `q` to quit. The engine's `docs/user-guide.md` has the rest.

## 11. Publishing a static channel, and what a web browser sees

Copy the folder to any host that serves files. There is nothing to configure, and no program runs. The folder's address is the channel: `https://example.org/news/`, or the root of a site, `https://example.org/`.

Before you tell anyone, check these:

- **Names.** `100.tti`, not `100.TTI`. Hexadecimal digits in capitals: a receiver asks for `1A0.tti`, and a case-sensitive host does not answer `1a0.tti`. The folder may be any name that is not a page number, `contents` or `wall`.
- **Media types.** A page file may arrive as `text/plain` or `application/octet-stream`, or as `text/x-teletext-tti` for TTI and `application/x-teletext-t42` for T42. `channel.ttx` may arrive as anything but `text/html`. `contents.txt` needs `text/plain` or `application/octet-stream`. Anything served as `text/html` is refused. Python's server sends `application/octet-stream` for all but `contents.txt`, and that works. What GitHub Pages and other hosts send was not measured.
- **`https`.** Plain `http` works, and the receiver marks the page. An `https` channel may not link to an `http` one.
- **Probe it,** from outside your network, with no `--allow-local`.

```
neottx probe https://example.org/news/
```

Then give people the address. Add a page or sub-page to open there: `https://example.org/news/102`, `https://example.org/news/102/0002`. For a link from a web page or another program, put `neottx://` before the whole address. It opens the browser, if it is installed:

```html
<a href="neottx://https://example.org/news/">Open in NeoTeletext</a>
```

### What a web browser sees

Most people who get your address have only a web browser. A static host answers them as it answers anything: a listing or a 404 at the folder, a 404 at `/news/102`, and a download at `100.tti`.

`neottx html` answers them. Give it the folder and the address the channel will have. It writes `index.html`, a small page naming the channel with an "Open in NeoTeletext" link, and `NNN/index.html` for each page. It needs a `channel.ttx`.

```sh
neottx html . --address https://example.org/news/ --public 101
ls index.html 100/index.html 101/index.html
```

Every host serves `index.html` at a folder, and no reader asks for it, so these files change nothing for a receiver. A folder named like a page belongs to the channel and is not a channel of its own, so a receiver still finds `102.tti`. Hosts commonly redirect `/news/102` to `/news/102/` and serve that file. Python's server did. What other hosts do was not measured.

A page's file has `noindex` and shows nothing of the page, unless you name the page with `--public`. A public page's file holds its title, a picture of the page and its text, hidden and declared for search engines. Give `--public` once for each page. Link previews and lists of public pages for search engines are not built (TODO-1992). Without `index.html` a channel still works, and a web visitor gets whatever the host gives.

Nothing on a static host can stop `100.tti` being read as a file by anyone who asks. A page that only some viewers may see needs a live channel.

## 12. How a live channel works

A live channel is a program. The Rust server speaks the teletext wire to viewers, and your program speaks JSON to the server.

```
 receiver  <-- WebSocket, teletext packets -->  teletext-server  <-- lines of JSON -->  your program
                                                                     standard input and output
```

- **One program serves every viewer.** It never handles a socket or a packet.
- **The server keeps no pages.** It asks your program for each one. The kits keep what you publish, and answer those questions for you.
- **A connection is one tab,** with one selection. A **session** is one viewer, across their tabs and reconnections, for 5 minutes after the last one closes.

The server answers only a few addresses for each channel: `channel.ttx`, which it writes for you, the WebSocket at `push`, and a small web page. It serves no files. A live channel has no `contents.txt` or `.tti` files. Your program gives the contents as a list of pages, and may read `.tti` files itself to publish them.

`channel.ttx` is generated, with your channel's name, initial page `100` and `"push":{"input":true}`. You do not write it, and at this commit neither of those last two can be changed. So your first page must be 100, and every key the viewer presses goes to your program.

Here are the first lines between the server and the program of section 13, shortened. The server said:

```text
{"type":"start","protocol":6,"epoch_ms":1793537341654,"standard":{...},"budgets":{...}}
{"type":"connected","connection":1,"session":1836582237850624,"request":1,"cookies":[],"selection":null,"path":null,"query":null}
{"type":"selected","connection":1,"request":2,"path":"200","page":"200","sub":"3F7F","query":null}
{"type":"input","connection":1,"page":"200","sub":"0000","lost":false,"event":{"kind":"key","action":"press","key":"ArrowUp","text":null,"base":null}}
```

The program answered:

```text
{"type":"reply","connection":1,"request":1,"magazines":[...],"selected":{"page":"100","sub":"0000","rows":[...],...}}
{"type":"page","connections":[1],"request":2,"page":{"page":"200","sub":"0000","rows":[...],...}}
```

The kits do all of that. To write a program without one, `docs/applications.md` in the server's repository is the whole protocol, and [`servers.md`](servers.md) section 2.16 has a program with no kit.

## 13. A live channel, step by step

The same channel twice, in TypeScript and Python. It has a shared front page, a clock that changes by itself, and a page of each viewer's own that answers their keys.

Work in the folder above `news`.

```sh
cd ..
```

### TypeScript

The kit is a built tarball, not on a registry. Take it from any channel's `vendor/`, such as `neoteletext-server-channel-home-www.neoteletext.com/vendor/`, or make one with `scripts/release.sh` in `neoteletext-server-ts-protocol`. `KITS` below is that folder.

```sh
mkdir -p hello-ts/vendor
cp "$KITS"/neoteletext-server-ts-protocol-6.0.0.tgz hello-ts/vendor/
cat > hello-ts/package.json <<'EOF'
{
  "name": "hello-channel",
  "private": true,
  "type": "module",
  "engines": { "node": ">=22.18.0" },
  "dependencies": {
    "neoteletext-server-ts-protocol": "file:vendor/neoteletext-server-ts-protocol-6.0.0.tgz"
  }
}
EOF
(cd hello-ts && npm install --ignore-scripts --no-audit --no-fund)
```

`hello-ts/main.ts`:

```ts hello-ts/main.ts
// A live channel: a shared front page, a clock that changes by itself, and
// a page of each viewer's own that answers their keys.
import { type Application, type Context, type Input, Colour, Key, Screen, pressed, runChannel } from "neoteletext-server-ts-protocol";

const FRONT = 0x100;
const CLOCK = 0x101;
const COUNTER = 0x200;
const SECOND_MS = 1000;

function front(): Screen {
  const screen = new Screen();
  screen.header("HELLO");
  screen.doubleHeight(2, 0, Colour.Yellow, "Hello, teletext");
  screen.coloured(5, 0, Colour.White, "101  The time");
  screen.coloured(6, 0, Colour.White, "200  Your own counter");
  screen.fastext([CLOCK, COUNTER, null, null]);
  screen.coloured(24, 0, Colour.Red, "Clock");
  screen.coloured(24, 10, Colour.Green, "Counter");
  return screen;
}

function clock(context: Context): Screen {
  const screen = new Screen();
  screen.header("HELLO");
  screen.coloured(2, 0, Colour.Cyan, new Date(context.epochMs()).toISOString());
  screen.indexLink(FRONT);
  return screen;
}

function counter(count: number): Screen {
  const screen = new Screen();
  screen.header("HELLO");
  screen.doubleHeight(2, 0, Colour.Green, `Count ${count}`);
  screen.text(6, 0, "Up and Down change it. Only you see it.");
  screen.indexLink(FRONT);
  return screen;
}

class Hello implements Application {
  readonly #counts = new Map<number, number>();

  pages() {
    return [
      { page: FRONT, title: "Hello", section: "Start" },
      { page: CLOCK, title: "The time" },
      { page: COUNTER, title: "Your own counter" },
    ];
  }

  start(context: Context): void {
    context.publish("channel", FRONT, front());
    context.publish("channel", CLOCK, clock(context));
    context.wakeIn(SECOND_MS);
  }

  wake(context: Context): void {
    context.publish("channel", CLOCK, clock(context));
    context.wakeIn(SECOND_MS);
  }

  opened(session: number, page: number, context: Context): void {
    if (page === COUNTER) {
      context.publish(session, COUNTER, counter(this.#counts.get(session) ?? 0));
    }
  }

  input(session: number, page: number, input: Input, context: Context): boolean {
    if (page !== COUNTER) {
      return false;
    }
    const step = pressed(input, Key.Up) ? 1 : pressed(input, Key.Down) ? -1 : 0;
    if (step === 0) {
      return false;
    }
    const count = (this.#counts.get(session) ?? 0) + step;
    this.#counts.set(session, count);
    context.publish(session, COUNTER, counter(count));
    return true;
  }

  ended(session: number): void {
    this.#counts.delete(session);
  }
}

await runChannel([new Hello()]);
```

The things to notice:

- Page numbers are hexadecimal: `0x100`, not `100`.
- `publish("channel", ...)` makes one shared copy for everyone. `publish(session, ...)` makes one viewer's own, which that viewer sees in place of the channel's.
- Publishing a page again is how a page changes. You send the whole page and the server sends each viewer only the rows that changed.
- `pages()` is the channel's list of pages. A page not in it cannot be published.
- `input` returns `true` when it took the key. Otherwise the kit uses it to move: three digits select a page, the coloured keys and F1 to F4 follow the page's `fastext` links, and a click on a printed page number or a row 24 prompt follows it. `ownsDigits` and `ownsColourKeys` in `pages()` keep those keys for your page.

### Python

The kit is in `neoteletext-server-channels/kits/python`, and has no dependencies. It is thin: it exists for the old Hackaday channel, so choose TypeScript for new work.

```sh
mkdir -p hello-py
cat > hello-py/pyproject.toml <<EOF
[project]
name = "hello-channel"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["neoteletext-app"]

[tool.uv.sources]
neoteletext-app = { path = "$PYTHON_KIT" }
EOF
```

`PYTHON_KIT` is the path of `kits/python`. `hello-py/main.py`:

```python hello-py/main.py
"""A live channel: a shared front page, a clock, and a page of each viewer's own."""

import asyncio
import datetime

from neoteletext_app.app import App
from neoteletext_app.event import Event
from neoteletext_app.screen import Colour, Screen

FRONT = 0x100
CLOCK = 0x101
COUNTER = 0x200
SECOND = 1.0


def front() -> Screen:
    screen = Screen()
    screen.header("HELLO")
    screen.double_height(2, 0, Colour.YELLOW, "Hello, teletext")
    screen.coloured(5, 0, Colour.WHITE, "101  The time")
    screen.coloured(6, 0, Colour.WHITE, "200  Your own counter")
    screen.fastext([CLOCK, COUNTER, None, None])
    screen.coloured(24, 0, Colour.RED, "Clock")
    screen.coloured(24, 10, Colour.GREEN, "Counter")
    return screen


def clock() -> Screen:
    screen = Screen()
    screen.header("HELLO")
    now = datetime.datetime.now(datetime.UTC)
    screen.coloured(2, 0, Colour.CYAN, now.isoformat(timespec="seconds"))
    screen.index_link(FRONT)
    return screen


def counter(count: int) -> Screen:
    screen = Screen()
    screen.header("HELLO")
    screen.double_height(2, 0, Colour.GREEN, f"Count {count}")
    screen.text(6, 0, "Up and Down change it. Only you see it.")
    screen.index_link(FRONT)
    return screen


class Hello(App):
    def __init__(self) -> None:
        super().__init__({FRONT: "Hello", CLOCK: "The time", COUNTER: "Your own counter"}, {FRONT: "Start"})
        self.counts: dict[int, int] = {}

    async def on_start(self) -> None:
        self.publish(FRONT, front())
        self.publish(CLOCK, clock())
        self.ticking = asyncio.create_task(self.tick())

    async def tick(self) -> None:
        while True:
            await asyncio.sleep(SECOND)
            self.publish(CLOCK, clock())

    async def on_open(self, session: int, page: int) -> None:
        if page == COUNTER:
            self.publish(COUNTER, counter(self.counts.get(session, 0)), session)

    async def on_input(self, session: int, page: int, event: Event) -> bool:
        if page != COUNTER:
            return False
        step = 1 if event.pressed_key("ArrowUp") else -1 if event.pressed_key("ArrowDown") else 0
        if step == 0:
            return False
        self.counts[session] = self.counts.get(session, 0) + step
        self.publish(COUNTER, counter(self.counts[session]), session)
        return True

    async def on_close(self, session: int) -> None:
        self.counts.pop(session, None)


Hello().run()
```

```sh
(cd hello-py && uv sync)
```

### Run them

The **channels file** tells the server what to serve. A `directory` is taken from the file's own folder, and a `folder` is letters, digits, `-` and `_`. It becomes the address, so do not use one that looks like a page number, `contents` or `wall`.

```sh
cat > channels.json <<'EOF'
{"channels":[
  {"folder":"hello","name":"Hello","command":["node","main.ts"],"directory":"hello-ts"},
  {"folder":"hellopy","name":"Hello from Python","command":["uv","run","--frozen","--no-dev","python","main.py"],"directory":"hello-py"}
]}
EOF
```

Start the server. It starts each program, and starts it again if it ends.

```sh
teletext-server --listen 127.0.0.1:8090 --origin http://127.0.0.1:8090 --channels channels.json --log-format text
```

```text
INFO teletext_server: serving version="0.1.0" listen=127.0.0.1:8090 origin="http://127.0.0.1:8090" channels="hello, hellopy"
INFO program: the program started channel="hello" program="node"
INFO program: the program started channel="hellopy" program="uv"
```

Check each one. The server is on `127.0.0.1`, and a local address needs `--allow-local`.

```sh
neottx probe http://127.0.0.1:8090/hello/ --allow-local 127.0.0.1 --select 101 --select 200
```

```text
channel     http://127.0.0.1:8090/hello/
entry file  read: "Hello"
initial     page 100
said        connecting
handshake   accepted: neottx.7
protocol    input protocol 7, WELCOME received
selection   100: a page in 309 ms
selection   101: a page in 5 ms
selection   200: a page in 300 ms
selection   8FC: DENIED 404 for "8FC" in 6 ms
result      no fault
```

`DENIED 404` for `8FC` is the channel doing the right thing. `DENIED 503` is a fault: your program did not answer within 5 seconds, or is not running. `probe` then exits with an error. You can meet this right after starting the server, before your program is ready: one run here got `selection 100: DENIED 503: the channel's program did not answer` for that reason, and the same probe passed a moment later.

Then try it by hand. Press F2, then Up:

```
neottx view http://127.0.0.1:8090/hello/ --allow-local 127.0.0.1
```

This was driven through a pseudo-terminal, with both programs. Up and Down changed the count, F1 and F2 followed the links, digits selected pages, and the clock changed by itself. `neottx view` sends every key to the channel, so `q` does not quit. Press Control-] to take the keys back.

**To change a program,** stop it and the server starts it again, at once if it had run for 5 seconds or more. Anything it wrote to standard error goes to the server's log. Never print to standard output: that is the protocol, and a stray line is refused.

## 14. More of what a live page can do

This program shows the rest, with a Python program after it. Every call below was run.

First write a page in French and one in Russian, for it to publish:

```sh
mkdir -p more-ts/vendor
cp hello-ts/vendor/*.tgz hello-ts/package.json more-ts/
mv more-ts/*.tgz more-ts/vendor/
(cd more-ts && npm install --ignore-scripts --no-audit --no-fund)
printf 'Bonjour à tous\nÇa coûte 5 €, déjà vu\n' > more-ts/fr.txt
printf 'Привет, мир\n' > more-ts/ru.txt
neottx write-text --set french --page 500 more-ts/fr.txt more-ts/500.tti
neottx write-text --set russian-bulgarian --page 501 more-ts/ru.txt more-ts/501.tti
```

`more-ts/main.ts`:

```ts more-ts/main.ts
import { readFileSync } from "node:fs";
import {
  type Application,
  type Context,
  type EncodedOpus,
  type Input,
  type PageDescription,
  type PageRequest,
  Colour,
  Key,
  Screen,
  Sixels,
  clicked,
  ffmpegOpus,
  pressed,
  runChannel,
} from "neoteletext-server-ts-protocol";

const FRONT = 0x100;
const STORY = 0x400;
const FRENCH = 0x500;
const RUSSIAN = 0x501;
const SEARCH = 0x600;
const CHIME = 0x700;
const PICTURE = 0x701;
const SOUND = { handle: 1, generation: 0 };
const SOUND_RATE = 8000;
const SOUND_SAMPLES = SOUND_RATE / 4;
const TONE_HZ = 440;
const TONE_LEVEL = 8000;
const SIXELS_WIDE = 20;
const SIXELS_HIGH = 12;
const AN_HOUR_S = 3600;

function page(title: string, line: string): Screen {
  const screen = new Screen();
  screen.header("MORE");
  screen.coloured(1, 0, Colour.Yellow, title);
  screen.text(3, 0, line);
  screen.indexLink(FRONT);
  return screen;
}

function tone(): Int16Array {
  const samples = new Int16Array(SOUND_SAMPLES);
  samples.forEach((_, index) => {
    samples[index] = Math.round(TONE_LEVEL * Math.sin((2 * Math.PI * TONE_HZ * index) / SOUND_RATE));
  });
  return samples;
}

function cross(): Screen {
  const screen = new Screen();
  const sixels = new Sixels(SIXELS_WIDE, SIXELS_HIGH);
  for (let at = 0; at < SIXELS_HIGH; at += 1) {
    sixels.set(at, at, true);
    sixels.set(SIXELS_WIDE - 1 - at, at, true);
  }
  sixels.draw(screen, 2, 1, Colour.Green);
  return screen;
}

class More implements Application {
  readonly #queries = new Map<number, string>();
  #encoded: EncodedOpus | undefined;

  pages() {
    return [
      { page: FRONT, title: "More", section: "Examples" },
      { page: STORY, title: "A story in three sub-pages" },
      { page: FRENCH, title: "Bonjour", section: "Languages" },
      { page: RUSSIAN, title: "Privet" },
      { page: SEARCH, title: "Reads its address" },
      { page: CHIME, title: "Press Enter for a chime" },
      { page: PICTURE, title: "A mosaic drawn from code" },
    ];
  }

  start(context: Context): void {
    context.publish("channel", FRONT, page("More", "See 400, 500, 501, 600, 700 and 701"));
    // Sub-pages: one page, three screens, numbered 0001 to 0003 by the kit.
    context.publishSubpages("channel", STORY, [
      { screen: page("Part one", "It was a dark and stormy night."), title: "Part one" },
      { screen: page("Part two", "The rain fell."), title: "Part two" },
      { screen: page("Part three", "The end."), title: "Part three" },
    ]);
    // Languages: a TTI file keeps its character set. `Screen` has no call for one.
    context.publishTti("channel", FRENCH, readFileSync("500.tti", "utf8"));
    context.publishTti("channel", RUSSIAN, readFileSync("501.tti", "utf8"));
    context.publish("channel", CHIME, page("Press Enter for a chime", "Or click anywhere."));
    context.publish("channel", PICTURE, cross());
    // Sound: encoded once, here, and sent to each viewer who opens the page.
    this.#encoded = ffmpegOpus().sound(tone(), SOUND_RATE);
  }

  // Every selection comes here first, with the address's query and the cookies.
  request(session: number, selected: number, request: PageRequest | null): void {
    if (selected === SEARCH && request !== null) {
      this.#queries.set(session, request.query["q"] ?? "nothing");
    }
  }

  opened(session: number, opened: number, context: Context): void {
    if (opened === SEARCH) {
      context.publish(session, SEARCH, page("You asked for", this.#queries.get(session) ?? "nothing"));
    }
    if (opened === CHIME && this.#encoded !== undefined) {
      context.sound({ session }, { opus: { ...SOUND, ...this.#encoded } });
    }
  }

  input(session: number, on: number, input: Input, context: Context): boolean {
    if (on === CHIME && (pressed(input, Key.Enter) || clicked(input))) {
      context.sound({ session }, { play: { channel: 0, ...SOUND, page: CHIME } });
      context.log(`chime for session ${session}`);
      context.authorLog({ session }, "I", "chime played", CHIME);
      const connection = context.connection();
      if (connection !== null) {
        context.cookie(connection, "chimed", "yes", { maxAge: AN_HOUR_S, sameSite: "Strict" });
      }
      return true;
    }
    if (on === CHIME && pressed(input, "x")) {
      context.redirect(session, FRONT);
      return true;
    }
    return false;
  }

  ended(session: number): void {
    this.#queries.delete(session);
  }

  // What a web visitor may see of a page. Nothing, unless you say so here.
  describe(asked: number): PageDescription | null {
    return asked === FRONT ? { public: true, title: "More", text: "A channel of examples." } : null;
  }
}

await runChannel([new More()]);
```

`more.py`, in `hello-py` beside `main.py`, does the same in Python. Copy `500.tti` beside it first.

```sh
cp more-ts/500.tti hello-py/
```

```python hello-py/more.py
"""Sub-pages, another language, a query and a redirect."""

from pathlib import Path
from typing import Any

from neoteletext_app.app import App, PageDescription
from neoteletext_app.event import Event
from neoteletext_app.screen import Colour, Screen

FRONT = 0x100
STORY = 0x400
FRENCH = 0x500
SEARCH = 0x600


def page_of(title: str, line: str) -> Screen:
    screen = Screen(title=title)
    screen.header("MORE")
    screen.coloured(1, 0, Colour.YELLOW, title)
    screen.text(3, 0, line)
    screen.index_link(FRONT)
    return screen


def from_file(file: str) -> Screen:
    screen = Screen()
    screen.load_tti(Path(file).read_text(encoding="utf-8"))
    return screen


class More(App):
    def __init__(self) -> None:
        super().__init__({FRONT: "More", STORY: "A story", FRENCH: "Bonjour", SEARCH: "Reads its address"})
        self.queries: dict[int, str] = {}

    async def on_start(self) -> None:
        self.publish(FRONT, page_of("More", "See 400, 500 and 600"))
        self.publish(STORY, [page_of("Part one", "A dark and stormy night."), page_of("Part two", "The rain fell.")])
        self.publish(FRENCH, from_file("500.tti"))

    async def on_request(self, session: int, page: int, request: dict[str, Any] | None) -> None:
        if page == SEARCH and request is not None:
            self.queries[session] = request["query"].get("q", "nothing")

    async def on_open(self, session: int, page: int) -> None:
        if page == SEARCH:
            self.publish(SEARCH, page_of("You asked for", self.queries.get(session, "nothing")), session)

    async def on_input(self, session: int, page: int, event: Event) -> bool:
        if page == SEARCH and event.pressed_key("Enter"):
            self.redirect(session, FRONT)
            return True
        return False

    def describe(self, page: int) -> PageDescription | None:
        return PageDescription(title="More", text="A channel of examples.") if page == FRONT else None


More().run()
```

Add both to `channels.json`, restart the server and probe them:

```sh
cat > channels.json <<'EOF'
{"channels":[
  {"folder":"hello","name":"Hello","command":["node","main.ts"],"directory":"hello-ts"},
  {"folder":"hellopy","name":"Hello from Python","command":["uv","run","--frozen","--no-dev","python","main.py"],"directory":"hello-py"},
  {"folder":"more","name":"More","command":["node","main.ts"],"directory":"more-ts"},
  {"folder":"morepy","name":"More from Python","command":["uv","run","--frozen","--no-dev","python","more.py"],"directory":"hello-py"}
]}
EOF
```

```
neottx probe http://127.0.0.1:8090/more/ --allow-local 127.0.0.1 --select 400 --select 400/0002 --select 500 --select 501 --select '600?q=teletext' --select 700 --select 701
```

```text
selection   100: a page in 326 ms
selection   400: a page in 13 ms
selection   400/0002: a page in 301 ms
selection   500: a page in 7 ms
selection   501: a page in 301 ms
selection   600?q=teletext: a page in 7 ms
selection   700: a page in 335 ms
selection   701: a page in 6 ms
selection   8FC: DENIED 404 for "8FC" in 7 ms
result      no fault
```

**Sub-pages.** `publishSubpages` numbers them by place: one sub-page is 0000, and 2 to 79 are 0001 to 0079. In Python, give `publish` a list. To change one sub-page without the others, use `put` and `remove`, which name sub-codes, or `subcodes=` in Python. A page's sub-page list reaches the receiver by itself, and the title of each is what you gave. The viewer steps with the browser's controls, and each step comes to your program as a new selection. `neottx view` cannot step a live page yet: `probe --select 400/0002` shows the sub-page is served.

**Languages.** `Screen` writes English only, and folds any other character to its nearest: `é` becomes `e`, and what it cannot fold becomes `?`. It has no call that sets a character set. For any other language, write the page with `neottx write-text`, then publish the file: `publishTti` in TypeScript, `load_tti` in Python, which keeps the `OL,28` line and any X/26 marks. If the words change as the program runs, run `neottx write-text` from the program.

**Input.** Your program is sent every key, click, wheel turn and pointer move on the page on screen, whether it wants them or not. Ignore what you do not use. A key has an `action`, `press`, `repeat` or `release`, and a `key`, a W3C `KeyboardEvent.key` name such as `ArrowUp`, `Enter` or `a`. A mouse event has a `column` and a `row`. A release with `lost` set means the key never came up, because the viewer left. Not every receiver reports releases: `neottx view` does not, except in a terminal with the Kitty keyboard protocol. A typed character is `typed(input)` or `character(input)` in TypeScript, and `event.typed` or `event.character` in Python. Draw what the viewer types on the page yourself, because the receiver draws nothing. `screen.cursor` places a cursor. In the browser, some keys never reach you: those with the browser's modifier, Command on macOS and Control-Shift elsewhere. Reference section 17 covers forms, and [DOC-1933](../PROTOCOL.html#DOC-1933) covers when a page is focused for input.

**Links.** Use `fastext` for the coloured keys: the kit follows those. `keyLink`, `numberLink` and `textLink` are the program's `LN`, `LK` and `LT`. They travel with the sub-page as a LINKS record, and the browser acts on them. But the kit does not follow `keyLink` on a key press, and `neottx view` does not read LINKS records yet, so F1 did nothing on a page that had only a `keyLink`. Use them for what `fastext` cannot carry: links that leave the channel, and links on the page's own text.

**Query.** The address `https://host/more/600?q=teletext` carries a query with the selection. It arrives in `request` before the page opens, and it goes with that one selection. It is untrusted: it comes from the viewer. Quote the page in your `--select` as above, and a shell will leave the `?` alone.

**Each viewer's own page.** Publish to `session` in place of `"channel"`. Forget the session in `ended`, which comes 5 minutes after the viewer goes. A restart of your program loses what it held in memory.

**Redirects.** `context.redirect(session, page)` moves the viewer to a page. Given an address, it moves them to another channel, after the receiver's notice of one second.

**Cookies.** `context.cookie(connection, name, value, options)` sets one, and the server refused nothing. A cookie is scoped to the channel's folder. Your program sees cookies in `request.cookies`, from when the connection opened, so one you set arrives on the next connection. Names starting `_` are the server's. `neottx` keeps no cookies between runs, so reading one back was not seen.

**Logs.** `context.log` writes to the server's log, and standard error does too. `context.authorLog` sends a line to the viewer's developer console.

**Sound.** Section 16.

**The UI library.** `neoteletext-server-ts-ui-components` is the way to build anything with forms, lists or menus. A page is a tree of components, as in React, with state and key handlers, and the library draws it and routes the keys. This ran as written, and Enter raised the count. It needs both tarballs in `package.json`, the kit's and `neoteletext-server-ts-ui-components-12.0.0.tgz`:

```ts ui-ts/main.ts
import { Colour, Key, runChannel } from "neoteletext-server-ts-protocol";
import { type Child, Component, ComponentChannel, Frame, h, isPress, type KeyEvent, Text } from "neoteletext-server-ts-ui-components";

class Counter extends Component<object, { readonly count: number }> {
  override state = { count: 0 };

  override focusable(): boolean {
    return true;
  }

  override render(): Child {
    return h(Text, { text: `Pressed ${this.state.count} times` });
  }

  override onKey(event: KeyEvent): boolean {
    if (!isPress(event, Key.Enter)) {
      return false;
    }
    this.setState({ count: this.state.count + 1 });
    return true;
  }
}

await runChannel([
  new ComponentChannel([
    {
      page: 0x100,
      title: "Hello",
      perViewer: true,
      root: () => h(Frame, { title: "Hello", background: Colour.Blue, prompts: [["Index", 0x100]] }, h(Counter, {})),
    },
  ]),
]);
```

Read real channels to see how far this goes. `neoteletext-server-channel-home-www.neoteletext.com` is the smallest, a set of pages of words. `-demosite` and `-uicomponentsdemo` show every feature, and `-hackaday` is a large site over a dataset.

**Tests.** The TypeScript kit has a harness that drives a channel as the server does, with no server. Run it with `node --test`:

```ts hello-ts/hello.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";
import { type Application, Colour, Screen } from "neoteletext-server-ts-protocol";
import { Harness, shows } from "neoteletext-server-ts-protocol/testing";

const hello: Application = {
  pages: () => [{ page: 0x100, title: "Hello" }],
  start(context) {
    const screen = new Screen();
    screen.doubleHeight(2, 0, Colour.Yellow, "Hello, teletext");
    context.publish("channel", 0x100, screen);
  },
};

test("the page says hello", () => {
  const harness = new Harness([hello]);
  harness.join(1, 0x100);
  assert.ok(shows(harness.shared(0x100), "Hello, teletext"));
});
```

[`servers.md`](servers.md) section 3.2 has more, and a probe of your own in code.

## 15. Publishing a live channel

You need a machine that runs the server and your programs, and something in front of it that holds the TLS certificate. The server speaks plain HTTP and never terminates TLS itself. Run it with the address viewers reach it at:

```
teletext-server --listen 127.0.0.1:8090 --origin https://teletext.example.org --channels channels.json --state /var/lib/neoteletext --admin-listen 127.0.0.1:8091
```

| Option | What it does |
|---|---|
| `--listen` | Where it accepts connections. `0.0.0.0:8090` by default |
| `--origin` | The address viewers reach it at. It goes in the `neottx://` link of the small web page |
| `--channels` | The channels file |
| `--state` | Where it keeps the session cookie's keys and its figures across a restart. Without it, sessions end at a restart |
| `--admin-listen` | Where `/metrics`, `/healthz`, `/readyz` and `/stats.json` are served. Keep it private |
| `--log-format` | `auto`, `json` or `text`. `RUST_LOG` chooses which events |

A channel in the folder `mine` is then at `https://teletext.example.org/mine/`. Put a proxy in front that passes WebSocket upgrades and the `Host` header. The project's own deployment uses Caddy, in `deploy/ionos/` in the server's repository. This block has the same form as those files, and was not run for this guide:

```
teletext.example.org {
	reverse_proxy 127.0.0.1:8090
}
```

The project never sends `Strict-Transport-Security`: `http` and `ws` are supported on purpose.

A viewer's connection is `wss://teletext.example.org/mine/push`. It is on the same origin as the channel, always. A proxy that refuses the upgrade makes a channel unreachable, because there is no fallback to HTTP. A WebSocket from a web page's script is refused with 403, as it carries an `Origin` header, and one that does not offer the subprotocol `neottx.7` gets 426.

A program can also run as a service of its own and connect to the server through a Unix socket, so it outlives a restart: `{"folder":"mine","name":"Mine","socket":"sockets/mine.sock"}`. [`servers.md`](servers.md) section 1.8 covers this and systemd.

Then, from outside:

```
neottx probe https://teletext.example.org/mine/
```

`/stats.json` on the administration listener shows each channel's figures, among them `refused`, the lines of yours the server refused, which should stay 0.

### What a web browser sees

The server answers a web browser by itself. You do nothing. This is from the `hello` channel above, with `--origin https://teletext.example.org`:

| Request | Answer |
|---|---|
| `/hello/`, `/hello/contents`, `/hello/wall` | 200, a small web page naming the channel, with an "Open in NeoTeletext" link to `neottx://https://teletext.example.org/hello/` and a "Get NeoTeletext" link |
| `/hello/100`, `/hello/100/0002`, `/hello/1fe` | 200, the same page, its link naming that place |
| `/hello` | 308 to `/hello/` |
| `/hello/100/` | 308 to `/hello/100` |
| `/hello/channel.ttx` | 200, `application/json` |
| `/hello/push` | 426 without a WebSocket upgrade |
| `/hello/100.tti`, `/hello/contents.txt`, `/hello/902`, `/` | 404 |

That page runs no script and shows nothing of your pages. A page's own address has `noindex` as well, and looks the same whether the page exists or not, so an address says nothing of what is behind it.

**A page is public only if your program says so,** page by page. When a web visitor or a search engine comes to a page's address, the server asks your program with `describe`, which carries the page number and nothing else. So the answer cannot depend on a viewer: it goes to everyone for a minute. Add a `describe` method, as both programs in section 14 did for page 100. The server then answers that address with the page's title, a picture of the page, the offer to open it, and the text you gave, hidden and declared for search engines. All of it is readable by anyone. A `PageSpec` in the UI library has a `describe()` of its own.

The picture is drawn from the channel's copy of the page, so a page published only to sessions cannot be public. A program that does not answer within 2 seconds is taken to have said no. [DOC-1975](../PROTOCOL.html#DOC-1975) has the rest.

## 16. Sound

| Channel | Sound |
|---|---|
| Live, TypeScript | Works. `ffmpegOpus` encodes with ffmpeg and libopus, which must be on the host, and `context.sound` sends it |
| Live, Python | The kit has only `sound_object`, PCM encoded by the server as IMA ADPCM. Desktop and phone receivers do not play it |
| Static | No sound a desktop browser plays. `neottx sound` writes IMA ADPCM or PCM packets for microcontroller receivers, not Opus |

The desktop browser plays Opus and nothing else. In a live channel a sound has two steps, as in section 14. You send the sound once to a viewer, with a `handle`, and it is stored. Then a `play` command names the handle, on one of four channels, and may give a gain, a fade and a loop. A sound with a `page` plays only while that page is open. Send it in `opened`, because in `joined` the connection does not exist yet. A sound is at most two minutes; `opusLive` and `opusPackets` stream one.

At these commits the server accepted the sound and the `play` command and refused nothing: after page 700 was opened and Enter pressed, `/stats.json` showed `"sound_records":3` and `"refused":0`. No receiver that plays sound was run, so nobody heard it. The demo site's `src/pages/audio/` plays real sounds.

For a static channel, `neottx sound --page 100 chime.wav chime.t42` turns a 16-bit WAVE file into packets, and `cat` adds them to a page's `NNN.t42`. A channel with such a page opens normally, but what it does depends on a receiver built with IMA ADPCM, which the desktop builds leave out.

## 17. Addresses

A channel has one URL map. It is the same for every channel, and a channel cannot add to it. `<channel>` is an `http` or `https` address ending in `/`. [DOC-1779](../PROTOCOL.html#DOC-1779) is the full text, and `crates/neoteletext-web/src/map/conformance.tsv` in the engine is the table every program tests against.

| Address | Opens |
|---|---|
| `<channel>` | The channel, at its initial page |
| `<channel>302` | Page 302 |
| `<channel>302/0002` | Sub-page 0002 of page 302 |
| `<channel>302?name=value` | Page 302, with a query for the program. A static channel ignores it |
| `<channel>contents` | The contents |
| `<channel>wall` | The wall of pages |

The address is normalised to one spelling: `1fe` becomes `1FE`, `302/` becomes `302`, and `302.tti` becomes `302`. It is refused if it is not on the map: `30`, `902`, `302/2`, `302/3F7F`, `WALL`, or anything with a `#`, because a page is never a fragment on an `http` address. `#` works only for `file:` addresses in the browser.

**A receiver asks a static channel for files, never for those addresses.** It goes from `<channel>302` to `302.tti` by rule. Here is what a host saw when a channel opened:

```text
GET /news/channel.ttx    200
GET /news/index.t42      404
GET /news/100.tti        200
```

For each page it tries `NNN.tti`, then `NNN.t42`. On a live channel, it fetches `channel.ttx`, then opens the WebSocket and selects pages over it.

| Name | Static | Live |
|---|---|---|
| `channel.ttx` | Your file | Generated |
| `push` | None | The WebSocket |
| `contents.txt` | Your file | None. The program gives the index |
| `index.t42` | Your file | None |
| `NNN.tti`, `NNN.t42` | Your files | None |
| `NNN/SSSS.t42`, `NNN/SSSS.tti`, `NNN/P.sub` | Your files | None |

**`http` and `ws`.** A channel's WebSocket is at `<channel>push`, by rule: `wss://` for a channel at `https://`, and `ws://` for one at `http://`. Both are supported. The receiver marks a plain connection, with the red `!` in row 0, and in the browser "Not secure" in the strip.

**`neottx://`** is a link that opens the receiver. It wraps a whole address and adds nothing: `neottx://https://example.org/news/102`. `neottx` follows it too. The browser registers the scheme with the operating system when it is installed. Inside your own pages, links stay plain addresses.

**A channel's identity** is its origin and folder, compared exactly. A folder inside a channel's folder is a different channel, and shares nothing with it, unless it is named by a page number. Cookies, links and redirects stop at that boundary. Going from one channel to another is "leaving", and the receiver says so.

**A folder on your own computer.** The browser's code opens a local folder as a channel by the same rules, and each local file as its own channel, so you can try pages before you upload them. That was not run. `neottx` does not open folders: it takes one file at a time.

## 18. Limits

The limits are defined in [the channel format](../PROTOCOL.html#DOC-1786) and in [every address is accepted](../PROTOCOL.html#DOC-1807) and [reserved and recommended page numbers](../PROTOCOL.html#DOC-1808). This section collects them for a channel's author.

| What | Most |
|---|---|
| `channel.ttx` | 16,384 bytes |
| `contents.txt` | 65,536 bytes, 1,000 lines |
| A page file, `index.t42` | 262,144 bytes |
| Pages in a channel | 2,022 numbers, 800 of them typeable |
| Pages in a magazine | 253, or 251 in magazine 1 |
| Sub-pages of a page | 8,190 |
| A title | 120 characters in `contents.txt` and a program's index; 40 for a sub-page |
| A link label | 9 characters, 8 for a link that leaves the channel |
| `LK` lines, `LT` lines | 8 of each on a sub-page |
| `services`, `aliases` | 16 of each |
| A channel's `name` | 64 bytes |
| An address | 8,000 octets |
| A line of the program protocol | 16 MiB |
| A program's answer to a selection | 5 seconds, then DENIED 503 |
| A sound | Two minutes |

## 19. What is not built yet

Each of these is written somewhere as the plan, or is a gap you will meet.

| Thing | State at these commits |
|---|---|
| `presentation` in `channel.ttx` | [DOC-2037](../PROTOCOL.html#DOC-2037) describes it. The reader refuses it as an unknown member |
| `M.pag`, `NNN.ep1` | [DOC-2034](../PROTOCOL.html#DOC-2034) and [DOC-2039](../PROTOCOL.html#DOC-2039) describe them. There are no magazine lists or EP1 pages in a channel |
| A tool that builds a channel | [DOC-2034](../PROTOCOL.html#DOC-2034) describes one in `neottx`. There is no such command (TODO-1224): use `convert`, `contents`, `html` and `cat` |
| Choosing a live channel's first page | The server always says `initial_page` 100 and `input` true |
| `neottx text`, `show`, `render` and `list` on a live channel | They send no selection, so they see only the initial page (TODO-1529). Use `probe --select` and `view` |
| LINKS and SUBPAGES records in `neottx view` | Not used, so `keyLink` does nothing there, and Left and Right do not step a live page (TODO-1529) |
| `LK` lines and aliases in `neottx view` | Typing the number did not follow them |
| Logging in | Sessions exist, identity does not. A program sees only a session number |
| Opus in the Python kit | Not built (TODO-1310) |
| Levels 2.5 and 3.5 on a live channel | Packets X/26 to X/28 go with a sub-page through TTI. How object pages reach a receiver is not designed (TODO-2023 item 7) |
| The Cloudflare host | Its code exists and has never run |

## 20. Where to read next

| To | Read |
|---|---|
| Learn everything a page can do, level by level | [`teletext-reference.md`](teletext-reference.md) |
| Run the server, and program it in depth | [`servers.md`](servers.md) |
| See the protocol whole | [`PROTOCOL.html`](../PROTOCOL.html), the one definition of it |
| See the channel format, including what is proposed | [DOC-1786](../PROTOCOL.html#DOC-1786) |
| See the URL map and the wire | [DOC-1779](../PROTOCOL.html#DOC-1779), [DOC-1780](../PROTOCOL.html#DOC-1780) and [DOC-1782](../PROTOCOL.html#DOC-1782) |
| See input, key names and receivers | [DOC-1781](../PROTOCOL.html#DOC-1781) |
| See every message of the program protocol | `docs/applications.md` in `neoteletext-app-server` |
| See every `neottx` command | `docs/user-guide.md` in `neoteletext-engine` |
