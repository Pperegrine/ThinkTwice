/* Diagnostic-only OpenGL interposition: print the original link failure log. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
typedef void (*proc_t)(void);
typedef proc_t (*get_t)(const unsigned char *);
proc_t glXGetProcAddressARB(const unsigned char *name);
proc_t glXGetProcAddress(const unsigned char *name);
void glLinkProgram(unsigned int program);
static void *original_dlsym(void *handle, const char *name) {
    typedef void *(*sym_t)(void *, const char *);
    sym_t sym = (sym_t)dlvsym(RTLD_NEXT, "dlsym", "GLIBC_2.2.5");
    return sym(handle, name);
}
void *dlsym(void *handle, const char *name) {
    if (!strcmp(name, "glXGetProcAddressARB")) return glXGetProcAddressARB;
    if (!strcmp(name, "glXGetProcAddress")) return glXGetProcAddress;
    if (!strcmp(name, "glLinkProgram")) return glLinkProgram;
    return original_dlsym(handle, name);
}
static proc_t real_proc(const char *name) {
    static get_t get;
    if (!get) {
        void *lib = dlopen("libGL.so.1", RTLD_LAZY | RTLD_LOCAL);
        get = (get_t)original_dlsym(lib, "glXGetProcAddressARB");
    }
    return get((const unsigned char *)name);
}
void glLinkProgram(unsigned int program) {
    void (*link)(unsigned int) = (void (*)(unsigned int))real_proc("glLinkProgram");
    void (*query)(unsigned int, unsigned int, int *) = (void (*)(unsigned int,unsigned int,int *))real_proc("glGetProgramiv");
    void (*info)(unsigned int, int, int *, char *) = (void (*)(unsigned int,int,int *,char *))real_proc("glGetProgramInfoLog");
    link(program);
    int status = 1;
    query(program, 0x8B82, &status);
    if (!status) {
        char buffer[65536] = {0};
        int length = 0;
        info(program, sizeof(buffer)-1, &length, buffer);
        fprintf(stderr, "GL_LINK_DIAGNOSTIC program=%u original_info_log=%s\n", program, buffer);
        fflush(stderr);
    }
}
proc_t glXGetProcAddressARB(const unsigned char *name) {
    if (!strcmp((const char *)name, "glLinkProgram")) return (proc_t)glLinkProgram;
    return real_proc((const char *)name);
}
proc_t glXGetProcAddress(const unsigned char *name) { return glXGetProcAddressARB(name); }
