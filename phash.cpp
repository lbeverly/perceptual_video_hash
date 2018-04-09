#include <iostream>
#include <cstdint>
#include <string>

#include "pHash-config.h"
#include "pHash.h"


using namespace std;

int main(int argc, char ** argv) {
    if (argc < 2) {
        cerr << "Must specify video file" << endl;
        exit(1);
    }

    string s(argv[1]);

    int length = 0;
    ulong64* hashes = ph_dct_videohash(s.c_str(), length);

    for(int i = 0; i < length; ++i) {
        cout << hashes[i] << endl;
    }
    delete[] hashes;
}

