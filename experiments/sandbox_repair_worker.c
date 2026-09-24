#include <errno.h>
#include <stdio.h>
#include <string.h>

static void trim_newline(char *value) {
    value[strcspn(value, "\r\n")] = '\0';
}

int main(int argc, char **argv) {
    if (argc != 3) {
        return 2;
    }
    FILE *input = fopen(argv[1], "r");
    if (input == NULL) {
        return 3;
    }
    char reference_color[256] = {0};
    char simulator_color[256] = {0};
    char probe_path[4096] = {0};
    if (fgets(reference_color, sizeof(reference_color), input) == NULL ||
        fgets(simulator_color, sizeof(simulator_color), input) == NULL) {
        fclose(input);
        return 4;
    }
    (void)fgets(probe_path, sizeof(probe_path), input);
    fclose(input);
    trim_newline(reference_color);
    trim_newline(simulator_color);
    trim_newline(probe_path);

    int strip_rule = simulator_color[0] == '#' && strcmp(reference_color, simulator_color + 1) == 0;
    const char *probe_status = "not_requested";
    if (probe_path[0] != '\0') {
        FILE *probe = fopen(probe_path, "r");
        if (probe == NULL) {
            probe_status = (errno == EPERM || errno == EACCES) ? "denied" : "unavailable";
        } else {
            probe_status = "allowed";
            fclose(probe);
        }
    }

    FILE *output = fopen(argv[2], "w");
    if (output == NULL) {
        return 5;
    }
    if (strip_rule) {
        fprintf(output,
                "{\"rules\":[{\"field\":\"label.color\","
                "\"transform\":\"strip_leading_hash\","
                "\"evidence\":\"paired values differ only by a simulator leading hash\"}],"
                "\"probe_read\":\"%s\"}\n",
                probe_status);
    } else {
        fprintf(output, "{\"rules\":[],\"probe_read\":\"%s\"}\n", probe_status);
    }
    fclose(output);
    return 0;
}
