/* DOS 8086 installer helper: validate a destination and relocate runtime paths.
   MEDIA updates the installer's own working copy; PATCH updates its target. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <direct.h>
#include <ctype.h>

#define SLOT_SIZE 80
#define ROOT_LIMIT 48

static const char *dict_suffix = "\\GBPY.DAT";
static const char *bitmap_suffix = "\\SYSTEM\\CFSUNG16.B5Q";
static const char *main_suffix = "\\SYSTEM\\CHCGA12.FNT";
static const char *medium_suffix = "\\SYSTEM\\CHCGA10.FNT";
static const char *small_suffix = "\\SYSTEM\\CHCGA08.FNT";

static int ascii_letter(int ch)
{
    return (ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z');
}

static int allowed(int ch)
{
    return ascii_letter(ch) || (ch >= '0' && ch <= '9') ||
           ch == '_' || ch == '-' ||
           ch == '$' || ch == '~';
}

static int directory(const char *path)
{
    struct stat info;
    return stat(path, &info) == 0 && (info.st_mode & S_IFDIR) != 0;
}

static int exists(const char *path)
{
    struct stat info;
    return stat(path, &info) == 0;
}

static int root_syntax(const char *root)
{
    const char *part, *end;
    size_t length = strlen(root), base, extension;
    int has_dot;
    if (length < 4 || length >= ROOT_LIMIT ||
        !ascii_letter((unsigned char)root[0]) || root[1] != ':' ||
        root[2] != '\\' || root[length - 1] == '\\') return 0;
    for (part = root + 3; *part; part = end + (*end == '\\')) {
        end = strchr(part, '\\');
        if (!end) end = part + strlen(part);
        base = extension = 0;
        has_dot = 0;
        while (part < end) {
            if (*part == '.') {
                if (has_dot || !base || part + 1 == end) return 0;
                has_dot = 1;
            } else {
                if (!allowed(*part)) return 0;
                if (has_dot) ++extension;
                else ++base;
            }
            ++part;
        }
        if (!base || base > 8 || extension > 3) return 0;
        if (!*end) break;
    }
    return 1;
}

static int validate_root(const char *root, int must_exist)
{
    char parent[SLOT_SIZE];
    char *slash;
    if (!root_syntax(root)) return 0;
    strcpy(parent, root);
    slash = strrchr(parent, '\\');
    if (slash == parent + 2) parent[3] = '\0';
    else *slash = '\0';
    if (!directory(parent)) return 0;
    return must_exist ? directory(root) : !exists(root);
}

static int source_directory(const char *root, char *current)
{
    size_t index;
    if (!getcwd(current, SLOT_SIZE) || strlen(current) < 3 ||
        !ascii_letter((unsigned char)current[0]) || current[1] != ':' ||
        current[2] != '\\') return 0;
    for (index = 0; current[index] && root[index]; ++index)
        if (toupper((unsigned char)current[index]) !=
            toupper((unsigned char)root[index])) break;
    if (!current[index] && !root[index]) {
        puts("Setup medium and Windows destination are the same directory.");
        return 0;
    }
    if (!exists("GBPATH.EXE") || !exists("PHON.IME") ||
        !exists("GBPY.DAT") || !exists("SETUP.INF")) {
        puts("Current directory is not the complete Setup medium.");
        return 0;
    }
    return 1;
}

static int save_source(const char *root)
{
    char current[SLOT_SIZE], path[SLOT_SIZE];
    FILE *file;
    int failed = 0;
    if (!validate_root(root, 1) || !source_directory(root, current))
        return 0;
    sprintf(path, "%s\\GBSRC.BAT", root);
    file = fopen(path, "wb");
    if (!file) return 0;
    if (fprintf(file, "@ECHO OFF\r\n%c:\r\nCD %s\r\n",
                toupper((unsigned char)current[0]), current + 2) < 0)
        failed = 1;
    if (fclose(file) != 0) failed = 1;
    if (failed) {
        remove(path);
        return 0;
    }
    return 1;
}

static int marker(const char *root, const char *name, int create)
{
    char path[SLOT_SIZE];
    FILE *file;
    if (root) sprintf(path, "%s\\%s", root, name);
    else strcpy(path, name);
    if (!create) return !exists(path) || remove(path) == 0;
    file = fopen(path, "wb");
    if (!file) return 0;
    if (fclose(file) == 0) return 1;
    remove(path);
    return 0;
}

static int patch(FILE *file, long at, const char *replacement)
{
    unsigned char slot[SLOT_SIZE];
    size_t length = strlen(replacement);
    if (at < 0 || length >= SLOT_SIZE) return 0;
    memset(slot, 0, sizeof(slot));
    memcpy(slot, replacement, length);
    return fseek(file, at, SEEK_SET) == 0 &&
           fwrite(slot, 1, sizeof(slot), file) == sizeof(slot) &&
           fflush(file) == 0;
}

static int setup_default(const char *root)
{
    FILE *source, *target;
    char line[256];
    int changed = 0, failed = 0;
    source = fopen("SETUP.INF", "rb");
    if (!source) return 0;
    target = fopen("SETUP.$$$", "wb");
    if (!target) { fclose(source); return 0; }
    while (fgets(line, sizeof(line), source)) {
        if (strstr(line, "defdir = ") == line + 4) {
            if (++changed != 1 || fprintf(target, "    defdir = %s\r\n", root) < 0)
                failed = 1;
        } else if (fputs(line, target) == EOF) failed = 1;
    }
    if (ferror(source)) failed = 1;
    if (fclose(target) != 0) failed = 1;
    fclose(source);
    if (failed || changed != 1) { remove("SETUP.$$$"); return 0; }
    if (remove("SETUP.INF") != 0 || rename("SETUP.$$$", "SETUP.INF") != 0)
        return 0;
    return 1;
}

/* Program Manager .GRP has a 16-bit additive checksum at byte 4. A saved
   odd-length group may end with an unchecked padding byte. Its rectangle at
   byte 10 is too short for the second icon row on a CGA screen. */
static int layout_group(const char *root, const char *name, int cga)
{
    char path[SLOT_SIZE];
    unsigned char header[18], pair[2], rectangle[8], count_bytes[2], position[4];
    unsigned long sum = 0;
    long length;
    size_t got;
    unsigned count, index, placed = 0, offset, coordinate, columns;
    FILE *file;
    sprintf(path, "%s\\%s", root, name);
    file = fopen(path, "r+b");
    if (!file) return 0;
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 48 ||
        length > 65535L || fseek(file, 0, SEEK_SET) != 0 ||
        fread(header, 1, sizeof(header), file) != sizeof(header) ||
        memcmp(header, "PMCC", 4) != 0 ||
        (unsigned short)(header[6] | header[7] << 8) != (unsigned short)length) {
        fclose(file);
        return 0;
    }
    if (fseek(file, 32, SEEK_SET) != 0 ||
        fread(count_bytes, 1, 2, file) != 2) {
        fclose(file);
        return 0;
    }
    count = count_bytes[0] | count_bytes[1] << 8;
    columns = cga && strcmp(name, "CMAIN.GRP") != 0 ? 5 : 4;
    if (count > 64 || 34UL + 2UL * count > (unsigned long)length) {
        fclose(file);
        return 0;
    }
    /* Reject malformed item offsets before changing any group byte. */
    for (index = 0; index < count; ++index) {
        if (fseek(file, 34L + 2L * index, SEEK_SET) != 0 ||
            fread(pair, 1, 2, file) != 2) {
            fclose(file);
            return 0;
        }
        offset = pair[0] | pair[1] << 8;
        if (offset && (offset < 34 + 2 * count ||
                       (unsigned long)offset + 4 > (unsigned long)length)) {
            fclose(file);
            return 0;
        }
    }
    rectangle[0] = rectangle[1] = rectangle[2] = rectangle[3] = 0;
    rectangle[4] = 600 & 255;
    rectangle[5] = 600 >> 8;
    rectangle[6] = cga ? 150 : 250;
    rectangle[7] = 0;
    if (fseek(file, 10, SEEK_SET) != 0 ||
        fwrite(rectangle, 1, sizeof(rectangle), file) != sizeof(rectangle)) {
        fclose(file);
        return 0;
    }
    for (index = 0; index < count; ++index) {
        if (fseek(file, 34L + 2L * index, SEEK_SET) != 0 ||
            fread(pair, 1, 2, file) != 2) {
            fclose(file);
            return 0;
        }
        offset = pair[0] | pair[1] << 8;
        if (!offset) continue;
        coordinate = cga && columns == 5 ? 50 + 100 * (placed % columns) :
                                          60 + 140 * (placed % columns);
        position[0] = (unsigned char)(coordinate & 255);
        position[1] = (unsigned char)(coordinate >> 8);
        coordinate = cga ? 62 * (placed / columns) :
                           70 * (placed / columns);
        position[2] = (unsigned char)(coordinate & 255);
        position[3] = (unsigned char)(coordinate >> 8);
        if (fseek(file, offset, SEEK_SET) != 0 ||
            fwrite(position, 1, sizeof(position), file) != sizeof(position)) {
            fclose(file);
            return 0;
        }
        ++placed;
    }
    if (fseek(file, 4, SEEK_SET) != 0 ||
        fwrite("\0\0", 1, 2, file) != 2 || fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return 0;
    }
    sum = 0;
    while ((got = fread(pair, 1, 2, file)) != 0)
        if (got == 2) sum += pair[0] | pair[1] << 8;
    sum = (0x10000UL - (sum & 0xffff)) & 0xffff;
    pair[0] = (unsigned char)sum;
    pair[1] = (unsigned char)(sum >> 8);
    if (fseek(file, 4, SEEK_SET) != 0 || fwrite(pair, 1, 2, file) != 2 ||
        fclose(file) != 0) return 0;
    return 1;
}

static int layout_progman(const char *root, int cga)
{
    char path[SLOT_SIZE], line[256], padded[256];
    const char *replacement = cga ? "Window=0 0 640 200 3" :
                                    "Window=0 0 640 480 3";
    long at = -1, cursor;
    size_t width = 0, wanted = strlen(replacement);
    FILE *file;
    sprintf(path, "%s\\PROGMAN.INI", root);
    file = fopen(path, "r+b");
    if (!file) return 0;
    while ((cursor = ftell(file)) >= 0 && fgets(line, sizeof(line), file)) {
        if (strncmp(line, "Window=", 7) != 0) continue;
        if (at >= 0) { fclose(file); return 0; }
        at = cursor;
        width = strcspn(line, "\r\n");
        if (width < wanted || width + 2 >= sizeof(padded) ||
            line[width] != '\r' || line[width + 1] != '\n') {
            fclose(file);
            return 0;
        }
    }
    if (at < 0) { fclose(file); return 0; }
    memset(padded, ' ', width);
    memcpy(padded, replacement, wanted);
    padded[width] = '\r';
    padded[width + 1] = '\n';
    if (fseek(file, at, SEEK_SET) != 0 ||
        fwrite(padded, 1, width + 2, file) != width + 2 ||
        fclose(file) != 0) return 0;
    return 1;
}

/* The original Setup enables a missing-network startup warning. Its modal
   screen can appear after applications have opened, and its stock text is not
   GB2312. Keep the network driver choice, but suppress that warning in a
   completed installation on either display. */
static int layout_winini(const char *root)
{
    char path[SLOT_SIZE], line[256];
    long at = -1, cursor;
    int value = -1;
    FILE *file;
    sprintf(path, "%s\\WIN.INI", root);
    file = fopen(path, "r+b");
    if (!file) return 0;
    while ((cursor = ftell(file)) >= 0 && fgets(line, sizeof(line), file)) {
        if (strncmp(line, "NetWarn=", 8) != 0) continue;
        if (at >= 0 || strlen(line) != 11 ||
            (line[8] != '0' && line[8] != '1') ||
            line[9] != '\r' || line[10] != '\n') {
            fclose(file);
            return 0;
        }
        at = cursor + 8;
        value = line[8];
    }
    if (at < 0) return fclose(file) == 0;
    if (value == '1' && (fseek(file, at, SEEK_SET) != 0 ||
                         fwrite("0", 1, 1, file) != 1)) {
        fclose(file);
        return 0;
    }
    return fclose(file) == 0;
}

/* Setup fills these WIFE sections with absolute paths. Never replace its
   installed INI with the unconfigured copy on the source medium: WIFEMAN
   needs FontDrivers and DefaultFont before Program Manager can start. */
static int wife_ini(const char *root, const char *name)
{
    static const char driver_name[] =
        "CWIN3 BIG-5 \275X\264y\303\344\246r\247\316\305X\260\312\265{\246\241";
    char path[SLOT_SIZE], temporary[SLOT_SIZE], backup[SLOT_SIZE];
    char line[1024];
    FILE *source, *target;
    int section = 0, seen = 0, failed = 0;
    sprintf(path, "%s\\%s.INI", root, name);
    sprintf(temporary, "%s\\%s.WFT", root, name);
    sprintf(backup, "%s\\%s.WFB", root, name);
    source = fopen(path, "rb");
    if (!source) return 0;
    target = fopen(temporary, "wb");
    if (!target) { fclose(source); return 0; }
    while (fgets(line, sizeof(line), source)) {
        if (!strchr(line, '\n')) { failed = 1; break; }
        if (line[0] == '[') {
            section = 0;
            if (strcmp(line, "[FontDrivers]\r\n") == 0) section = 1;
            if (strcmp(line, "[DefaultFont]\r\n") == 0) section = 2;
            if (strcmp(line, "[OutlineHandTune]\r\n") == 0) section = 3;
            if (section) {
                if (seen & (1 << section)) { failed = 1; break; }
                seen |= 1 << section;
            }
            if (fputs(line, target) == EOF) failed = 1;
            if (section == 1 &&
                fprintf(target, "%s=%s\\system\\cffont.fod\r\n\r\n",
                        driver_name, root) < 0) failed = 1;
            if (section == 2 &&
                fprintf(target, "FontDriver=%s\\system\\cffont.fod\r\n"
                                "FontPackage=%s\\system\\cfsung.fon\r\n"
                                "Big5PartialTable=%s\\b5part.tbl\r\n",
                        root, root, root) < 0) failed = 1;
            if (section == 3 &&
                fprintf(target, "CFShouSung1=%s\\system\\cfsung16.b5q\r\n"
                                "CFShouSung2=%s\\system\\cfsung20.b5q\r\n\r\n",
                        root, root) < 0) failed = 1;
            if (failed) break;
            continue;
        }
        if (section == 1 || section == 3) continue;
        if (section == 2) {
            if (strncmp(line, "FontDriver=", 11) == 0 ||
                strncmp(line, "FontPackage=", 12) == 0 ||
                strncmp(line, "Big5PartialTable=", 17) == 0) continue;
        }
        if (fputs(line, target) == EOF) { failed = 1; break; }
    }
    if (ferror(source)) failed = 1;
    if (fclose(target) != 0) failed = 1;
    fclose(source);
    if (failed || seen != ((1 << 1) | (1 << 2) | (1 << 3))) {
        remove(temporary);
        return 0;
    }
    if (exists(backup) && remove(backup) != 0) {
        remove(temporary);
        return 0;
    }
    if (rename(path, backup) != 0) {
        remove(temporary); return 0;
    }
    if (rename(temporary, path) != 0) {
        rename(backup, path);
        remove(temporary);
        return 0;
    }
    return 1;
}

int main(int argc, char **argv)
{
    char ime_file[SLOT_SIZE], driver_file[SLOT_SIZE];
    char dict_path[SLOT_SIZE], bitmap_path[SLOT_SIZE];
    char main_path[SLOT_SIZE], medium_path[SLOT_SIZE], small_path[SLOT_SIZE];
    FILE *ime, *driver = NULL;
    long at_dict, at_bitmap, at_main = -1, at_medium = -1, at_small = -1;
    int cga, media;
    const char *root;
    if (argc == 3 && strcmp(argv[1], "CHECK") == 0) {
        if (validate_root(argv[2], 0)) return 0;
        puts("Invalid, missing-parent, or occupied destination.");
        return 1;
    }
    if (argc == 3 && strcmp(argv[1], "SOURCE") == 0) {
        char current[SLOT_SIZE];
        if (!validate_root(argv[2], 1) ||
            !marker(argv[2], "GBSRC.OK", 0) ||
            !source_directory(argv[2], current) ||
            !marker(argv[2], "GBSRC.OK", 1)) return 1;
        return 0;
    }
    if (argc == 3 && strcmp(argv[1], "SAVESRC") == 0) {
        if (save_source(argv[2])) return 0;
        puts("Could not save Setup medium directory.");
        return 1;
    }
    if (argc == 3 && strcmp(argv[1], "WIFE") == 0) {
        if (!validate_root(argv[2], 1) ||
            !marker(argv[2], "GBWIF.OK", 0) ||
            !wife_ini(argv[2], "WIFEMAN") ||
            !wife_ini(argv[2], "WIFERM") ||
            !marker(argv[2], "GBWIF.OK", 1)) {
            puts("WIFE font paths could not be repaired.");
            return 1;
        }
        puts("WIFE font paths repaired.");
        return 0;
    }
    if (argc == 4 && strcmp(argv[1], "LAYOUT") == 0 &&
        (strcmp(argv[2], "CGA") == 0 || strcmp(argv[2], "VGA") == 0)) {
        cga = strcmp(argv[2], "CGA") == 0;
        if (!validate_root(argv[3], 1) ||
            !marker(argv[3], "GBLAY.OK", 0) ||
            !layout_group(argv[3], "CMAIN.GRP", cga) ||
            !layout_group(argv[3], "CACCESOR.GRP", cga) ||
            !layout_group(argv[3], "CGAMES.GRP", cga) ||
            !layout_progman(argv[3], cga) ||
            !layout_winini(argv[3]) ||
            !marker(argv[3], "GBLAY.OK", 1)) {
            puts("Program Manager layout update failed.");
            return 1;
        }
        puts("Program Manager layout updated.");
        return 0;
    }
    media = argc == 4 && strcmp(argv[1], "MEDIA") == 0;
    if (argc != 4 || (!media && strcmp(argv[1], "PATCH") != 0) ||
        (strcmp(argv[2], "CGA") != 0 && strcmp(argv[2], "VGA") != 0)) {
        puts("Usage: GBPATH CHECK X:\\DIR or GBPATH MEDIA/PATCH CGA X:\\DIR");
        return 1;
    }
    root = argv[3];
    cga = strcmp(argv[2], "CGA") == 0;
    if (!validate_root(root, media ? 0 : 1)) return 1;
    if (!marker(media ? NULL : root, media ? "GBMED.OK" : "GBPCH.OK", 0))
        return 1;
    if (media) {
        strcpy(ime_file, "PHON.IME");
        strcpy(driver_file, "CGA.DRV");
    } else {
        sprintf(ime_file, "%s\\PHON.IME", root);
        sprintf(driver_file, "%s\\SYSTEM\\CGA.DRV", root);
    }
    sprintf(dict_path, "%s\\GBPY.DAT", root);
    sprintf(bitmap_path, "%s\\SYSTEM\\CFSUNG16.B5Q", root);
    sprintf(main_path, "%s\\SYSTEM\\CHCGA12.FNT", root);
    sprintf(medium_path, "%s\\SYSTEM\\CHCGA10.FNT", root);
    sprintf(small_path, "%s\\SYSTEM\\CHCGA08.FNT", root);
    ime = fopen(ime_file, "r+b");
    if (!ime) return 1;
    if (cga) {
        driver = fopen(driver_file, "r+b");
        if (!driver) { fclose(ime); return 1; }
    }
    /* Positions belong to the matching shipped IME/driver. No content scan. */
    at_dict = 9750L;
    at_bitmap = 9830L;
    at_main = 9194L;
    at_medium = 9354L;
    at_small = 9274L;
    if (!patch(ime, at_dict, dict_path) ||
        !patch(ime, at_bitmap, bitmap_path) ||
        (cga && (!patch(driver, at_main, main_path) ||
                 !patch(driver, at_medium, medium_path) ||
                 !patch(driver, at_small, small_path)))) {
        puts("Runtime path update failed.");
        if (driver) fclose(driver);
        fclose(ime);
        return 1;
    }
    if (driver) fclose(driver);
    fclose(ime);
    if (media && !setup_default(root)) {
        puts("SETUP.INF default directory update failed.");
        return 1;
    }
    if (!marker(media ? NULL : root, media ? "GBMED.OK" : "GBPCH.OK", 1))
        return 1;
    puts("Runtime paths updated.");
    return 0;
}
