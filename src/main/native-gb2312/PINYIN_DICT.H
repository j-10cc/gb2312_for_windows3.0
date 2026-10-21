/* Bounded, disk-backed PYI2 reader. Included only by PINYIN_NATIVE.C. */
#define INDEX_BYTES 14
#define MAX_KEY 63
#define PAGE_SIZE 9
#define MAX_CANDIDATES 512
#define MAX_PHRASE_BYTES 16
#define PHRASE_RECORD 81

/* The installer replaces these fixed-size, NUL-padded path slots. */
static char dictionary_path[80] = "C:\\WINDOWS\\GBPY.DAT";
static char bitmap_path[80] = "C:\\WINDOWS\\SYSTEM\\CFSUNG16.B5Q";
static WORD index_count;
static DWORD phrase_start, phrase_count;
static char key[MAX_KEY + 1], raw_key[MAX_KEY + 1];
static WORD key_length, candidate_count, candidate_total, candidate_page;
static WORD page_size = PAGE_SIZE;
static BYTE candidates[PAGE_SIZE][MAX_PHRASE_BYTES + 1];
static BYTE candidate_lengths[PAGE_SIZE];
static BYTE glyph[32];

static WORD WordAt(const BYTE *p)
{
    return (WORD)p[0] | ((WORD)p[1] << 8);
}

static DWORD DwordAt(const BYTE *p)
{
    return (DWORD)WordAt(p) | ((DWORD)WordAt(p + 2) << 16);
}

static BOOL ValidKey(const BYTE *p, WORD size)
{
    WORD j;
    BOOL ended = FALSE;
    if (!p[0]) return FALSE;
    for (j = 0; j < size; ++j) {
        if (!p[j]) ended = TRUE;
        else if (ended || p[j] < 'a' || p[j] > 'z') return FALSE;
    }
    return ended;
}

static BOOL ValidText(const BYTE *p, WORD size)
{
    WORD j;
    if (!size || size > MAX_PHRASE_BYTES || (size & 1)) return FALSE;
    for (j = 0; j < size; j += 2)
        if (p[j] < 0xA1 || p[j] > 0xF7 ||
            p[j+1] < 0xA1 || p[j+1] > 0xFE) return FALSE;
    return TRUE;
}

/* Validate the small single-character index, phrase bounds and end records.
 * The build verifier checks every phrase's ordering/text. At runtime validate
 * each record that is actually read; never scan the multi-megabyte phrase file
 * on startup. Resident storage is independent of dictionary size. */
static BOOL LoadIndex(void)
{
    HFILE file;
    BYTE header[8], entry[INDEX_BYTES], record[PHRASE_RECORD];
    char previous[64];
    LONG length;
    DWORD next, n;
    WORD i, count;
    file = _lopen(dictionary_path, OF_READ);
    if (file == HFILE_ERROR) return FALSE;
    if (_lread(file, header, 6) != 6 || memcmp(header, "PYI2", 4)) goto invalid;
    index_count = WordAt(header + 4);
    if (!index_count || index_count > 500) goto invalid;
    length = _llseek(file, 0L, 2);
    next = 6L + (DWORD)index_count * INDEX_BYTES;
    if (length < (LONG)next || _llseek(file, 6L, 0) != 6L) goto invalid;
    previous[0] = '\0';
    for (i = 0; i < index_count; ++i) {
        if (_lread(file, entry, INDEX_BYTES) != INDEX_BYTES ||
            !ValidKey(entry, 8) || lstrcmp(previous, (LPSTR)entry) >= 0 ||
            DwordAt(entry + 8) != next) goto invalid;
        lstrcpy(previous, (LPSTR)entry);
        count = WordAt(entry + 12);
        if (!count || count > MAX_CANDIDATES) goto invalid;
        next += (DWORD)count * 2L;
        if (next > (DWORD)length) goto invalid;
    }
    if (_llseek(file, next, 0) != (LONG)next ||
        _lread(file, header, 8) != 8 || memcmp(header, "PYP1", 4)) goto invalid;
    phrase_count = DwordAt(header + 4);
    phrase_start = next + 8L;
    if (phrase_count > 1000000L ||
        phrase_start + phrase_count * PHRASE_RECORD != (DWORD)length) goto invalid;
    previous[0] = '\0';
    for (n = 0; n < (phrase_count > 1 ? 2L : phrase_count); ++n) {
        next = phrase_start + (n ? phrase_count - 1 : 0) * PHRASE_RECORD;
        if (_llseek(file, next, 0) != (LONG)next ||
            _lread(file, record, PHRASE_RECORD) != PHRASE_RECORD ||
            !ValidKey(record, 64) || record[64] < 4 ||
            !ValidText(record + 65, record[64]) ||
            lstrcmp(previous, (LPSTR)record) > 0) goto invalid;
        lstrcpy(previous, (LPSTR)record);
    }
    _lclose(file);
    return TRUE;
invalid:
    _lclose(file);
    return FALSE;
}

/* Full-pinyin exact match, phrases first. Optional apostrophes are retained
 * in raw_key for ASCII fallback and removed only from the dictionary key. */
static void LoadPage(void)
{
    HFILE file;
    BYTE entry[INDEX_BYTES], record[PHRASE_RECORD];
    char lookup[MAX_KEY + 1];
    DWORD low, high, mid, first, last, start = 0, phrase_base;
    WORD i, j, count = 0, offset, phrase_matches = 0, ordinal;
    int order;
    candidate_count = candidate_total = 0;
    for (i = 0, j = 0; i < key_length; ++i)
        if (key[i] != 39) lookup[j++] = key[i];
    lookup[j] = '\0';
    if (!j) return;
    file = _lopen(dictionary_path, OF_READ);
    if (file == HFILE_ERROR) return;
    low = 0; high = phrase_count;
    while (low < high) {
        mid = low + (high - low) / 2;
        if (_llseek(file, phrase_start + mid * PHRASE_RECORD, 0) < 0L ||
            _lread(file, record, PHRASE_RECORD) != PHRASE_RECORD ||
            !ValidKey(record, 64)) goto done;
        order = lstrcmp((LPSTR)record, lookup);
        if (order < 0) low = mid + 1; else high = mid;
    }
    first = low;
    high = phrase_count;
    while (low < high) {
        mid = low + (high - low) / 2;
        if (_llseek(file, phrase_start + mid * PHRASE_RECORD, 0) < 0L ||
            _lread(file, record, PHRASE_RECORD) != PHRASE_RECORD ||
            !ValidKey(record, 64)) goto done;
        order = lstrcmp((LPSTR)record, lookup);
        if (order <= 0) low = mid + 1; else high = mid;
    }
    last = low;
    if (last > first) {
        if (last - first > MAX_CANDIDATES) goto done;
        phrase_matches = (WORD)(last - first);
    }
    phrase_base = phrase_start + first * PHRASE_RECORD;
    if (j <= 7) {
        low = 0; high = index_count;
        while (low < high) {
            mid = low + (high - low) / 2;
            if (_llseek(file, 6L + mid * INDEX_BYTES, 0) < 0L ||
                _lread(file, entry, INDEX_BYTES) != INDEX_BYTES ||
                !ValidKey(entry, 8)) goto done;
            order = lstrcmp((LPSTR)entry, lookup);
            if (!order) {
                count = WordAt(entry + 12);
                start = DwordAt(entry + 8);
                break;
            }
            if (order < 0) low = mid + 1; else high = mid;
        }
    }
    count += phrase_matches;
    page_size = phrase_matches ? 3 : PAGE_SIZE;
    if (!count || count > MAX_CANDIDATES) goto done;
    candidate_total = count;
    offset = candidate_page * page_size;
    if (offset >= count) { candidate_page = 0; offset = 0; }
    candidate_count = count - offset;
    if (candidate_count > page_size) candidate_count = page_size;
    for (i = 0; i < candidate_count; ++i) {
        ordinal = offset + i;
        if (ordinal < phrase_matches) {
            if (_llseek(file, phrase_base + (DWORD)ordinal * PHRASE_RECORD, 0) < 0L ||
                _lread(file, record, PHRASE_RECORD) != PHRASE_RECORD ||
                !ValidKey(record, 64) || lstrcmp((LPSTR)record, lookup) ||
                record[64] < 4 || !ValidText(record + 65, record[64])) goto failed;
            candidate_lengths[i] = record[64];
            memcpy(candidates[i], record + 65, record[64]);
        } else {
            if (_llseek(file, start + (DWORD)(ordinal - phrase_matches) * 2L, 0) < 0L ||
                _lread(file, candidates[i], 2) != 2 || !ValidText(candidates[i], 2))
                goto failed;
            candidate_lengths[i] = 2;
        }
        candidates[i][candidate_lengths[i]] = 0;
    }
    goto done;
failed:
    candidate_count = candidate_total = 0;
done:
    _lclose(file);
}
