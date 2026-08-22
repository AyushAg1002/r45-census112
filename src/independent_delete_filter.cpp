// Independent edge-deletion/filter pipeline for the R(4,5,22,112) census.
//
// Deliberately no nauty/Traces headers or libraries are used here.  This
// program parses and emits graph6 itself, enumerates every edge of every
// input graph, and applies a bitset Ramsey-property test.  Canonicalization
// is intentionally left to a later, separately checked stage.

#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace {

constexpr int kOrder = 22;
constexpr int kInputEdges = 113;
constexpr std::uint32_t kAllVertices = (std::uint32_t{1} << kOrder) - 1;

using Graph = std::array<std::uint32_t, kOrder>;

struct Options {
    std::string input;
    std::string output;
    std::string manifest;
    bool quiet = false;
};

[[noreturn]] void usage(const char* program, const std::string& error = {}) {
    if (!error.empty()) {
        std::cerr << "error: " << error << "\n\n";
    }
    std::cerr
        << "Usage: " << program
        << " --input INPUT.g6 --output VALID.g6 [--manifest RESULT.json]"
           " [--quiet]\n";
    std::exit(error.empty() ? 0 : 2);
}

Options parse_options(int argc, char** argv) {
    Options options;
    for (int i = 1; i < argc; ++i) {
        const std::string_view argument(argv[i]);
        auto require_value = [&](const char* name) -> std::string {
            if (++i == argc) {
                usage(argv[0], std::string("missing value after ") + name);
            }
            return argv[i];
        };
        if (argument == "--input") {
            options.input = require_value("--input");
        } else if (argument == "--output") {
            options.output = require_value("--output");
        } else if (argument == "--manifest") {
            options.manifest = require_value("--manifest");
        } else if (argument == "--quiet") {
            options.quiet = true;
        } else if (argument == "--help" || argument == "-h") {
            usage(argv[0]);
        } else {
            usage(argv[0], "unknown argument: " + std::string(argument));
        }
    }
    if (options.input.empty() || options.output.empty()) {
        usage(argv[0], "--input and --output are required");
    }
    if (options.input == options.output) {
        usage(argv[0], "input and output must be different files");
    }
    return options;
}

Graph decode_graph6(std::string record, std::uint64_t line_number) {
    if (!record.empty() && record.back() == '\r') {
        record.pop_back();
    }
    constexpr std::string_view header = ">>graph6<<";
    if (record.starts_with(header)) {
        record.erase(0, header.size());
    }
    if (record.empty()) {
        throw std::runtime_error("line " + std::to_string(line_number) +
                                 ": empty graph6 record");
    }

    const unsigned char first = static_cast<unsigned char>(record.front());
    if (first < 63 || first > 125) {
        throw std::runtime_error("line " + std::to_string(line_number) +
                                 ": unsupported graph6 order encoding");
    }
    const int order = static_cast<int>(first) - 63;
    if (order != kOrder) {
        throw std::runtime_error("line " + std::to_string(line_number) +
                                 ": expected order 22, found " +
                                 std::to_string(order));
    }

    constexpr std::size_t bit_count = kOrder * (kOrder - 1) / 2;
    constexpr std::size_t encoded_bytes = (bit_count + 5) / 6;
    if (record.size() != 1 + encoded_bytes) {
        throw std::runtime_error("line " + std::to_string(line_number) +
                                 ": malformed graph6 record length");
    }

    Graph graph{};
    std::size_t position = 0;
    for (int right = 1; right < kOrder; ++right) {
        for (int left = 0; left < right; ++left, ++position) {
            const unsigned char byte =
                static_cast<unsigned char>(record[1 + position / 6]);
            if (byte < 63 || byte > 126) {
                throw std::runtime_error("line " +
                                         std::to_string(line_number) +
                                         ": invalid graph6 data byte");
            }
            const unsigned value = byte - 63;
            if ((value >> (5 - position % 6)) & 1U) {
                graph[left] |= std::uint32_t{1} << right;
                graph[right] |= std::uint32_t{1} << left;
            }
        }
    }

    // graph6 requires unused low bits of the final sextet to be zero.
    constexpr std::size_t padding = encoded_bytes * 6 - bit_count;
    if constexpr (padding > 0) {
        const unsigned final_value =
            static_cast<unsigned char>(record.back()) - 63;
        if ((final_value & ((1U << padding) - 1U)) != 0) {
            throw std::runtime_error("line " +
                                     std::to_string(line_number) +
                                     ": nonzero graph6 padding bits");
        }
    }
    return graph;
}

std::string encode_graph6(const Graph& graph) {
    constexpr std::size_t bit_count = kOrder * (kOrder - 1) / 2;
    constexpr std::size_t encoded_bytes = (bit_count + 5) / 6;
    std::array<unsigned char, encoded_bytes> sextets{};

    std::size_t position = 0;
    for (int right = 1; right < kOrder; ++right) {
        for (int left = 0; left < right; ++left, ++position) {
            if ((graph[left] >> right) & 1U) {
                sextets[position / 6] |= 1U << (5 - position % 6);
            }
        }
    }
    std::string record(1 + encoded_bytes, '\0');
    record.front() = static_cast<char>(kOrder + 63);
    for (std::size_t index = 0; index < encoded_bytes; ++index) {
        record[1 + index] = static_cast<char>(sextets[index] + 63);
    }
    return record;
}

std::uint64_t edge_count(const Graph& graph) {
    std::uint64_t twice_edges = 0;
    for (const auto neighbours : graph) {
        twice_edges += std::popcount(neighbours);
    }
    return twice_edges / 2;
}

bool has_clique(const Graph& graph, std::uint32_t candidates, int need) {
    if (need == 0) {
        return true;
    }
    while (std::popcount(candidates) >= need) {
        const unsigned vertex = std::countr_zero(candidates);
        candidates &= candidates - 1;
        if (has_clique(graph, candidates & graph[vertex], need - 1)) {
            return true;
        }
    }
    return false;
}

Graph complement(const Graph& graph) {
    Graph result{};
    for (int vertex = 0; vertex < kOrder; ++vertex) {
        result[vertex] =
            kAllVertices & ~(graph[vertex] | (std::uint32_t{1} << vertex));
    }
    return result;
}

bool has_independent_set(const Graph& graph, int size) {
    return has_clique(complement(graph), kAllVertices, size);
}

bool deletion_creates_independent_five(const Graph& source, int left,
                                       int right) {
    // The source has no independent 5-set.  Deleting left--right changes only
    // that pair, so every newly created independent 5-set must contain both
    // endpoints.  Its other three vertices must form an independent triple
    // among the common non-neighbours of left and right.  Thus this test is
    // equivalent to a full independent-5 search in the child, while being
    // substantially cheaper.
    const std::uint32_t endpoints =
        (std::uint32_t{1} << left) | (std::uint32_t{1} << right);
    const std::uint32_t common_nonneighbours =
        kAllVertices & ~(source[left] | source[right] | endpoints);
    if (std::popcount(common_nonneighbours) < 3) {
        return false;
    }
    return has_clique(complement(source), common_nonneighbours, 3);
}

std::string json_escape(std::string_view value) {
    std::string escaped;
    escaped.reserve(value.size() + 8);
    for (const unsigned char character : value) {
        switch (character) {
            case '\\': escaped += "\\\\"; break;
            case '"': escaped += "\\\""; break;
            case '\n': escaped += "\\n"; break;
            case '\r': escaped += "\\r"; break;
            case '\t': escaped += "\\t"; break;
            default:
                if (character < 0x20) {
                    constexpr char hex[] = "0123456789abcdef";
                    escaped += "\\u00";
                    escaped += hex[character >> 4];
                    escaped += hex[character & 15];
                } else {
                    escaped += static_cast<char>(character);
                }
        }
    }
    return escaped;
}

void write_manifest(const Options& options, std::uint64_t input_records,
                    std::uint64_t total_deletions,
                    std::uint64_t valid_deletions, double elapsed_seconds) {
    if (options.manifest.empty()) {
        return;
    }
    std::ofstream manifest(options.manifest);
    if (!manifest) {
        throw std::runtime_error("cannot open manifest: " + options.manifest);
    }
#if defined(__clang__)
    constexpr std::string_view compiler_id = "Clang";
    constexpr std::string_view compiler_version = __clang_version__;
#elif defined(__GNUC__)
    constexpr std::string_view compiler_id = "GCC";
    constexpr std::string_view compiler_version = __VERSION__;
#elif defined(_MSC_VER)
    constexpr std::string_view compiler_id = "MSVC";
    constexpr std::string_view compiler_version = "_MSC_VER=";
#else
    constexpr std::string_view compiler_id = "unknown";
    constexpr std::string_view compiler_version = "unknown";
#endif
    manifest << std::fixed << std::setprecision(6)
             << "{\n"
             << "  \"implementation\": "
                "\"standalone C++20; no nauty/Traces code or library\",\n"
             << "  \"compiler\": {\n"
             << "    \"id\": \"" << json_escape(compiler_id) << "\",\n"
             << "    \"version\": \"" << json_escape(compiler_version)
             << "\",\n"
             << "    \"cplusplus\": " << __cplusplus << "\n"
             << "  },\n"
             << "  \"input\": \"" << json_escape(options.input) << "\",\n"
             << "  \"input_records\": " << input_records << ",\n"
             << "  \"input_order\": " << kOrder << ",\n"
             << "  \"input_edges_per_graph\": " << kInputEdges << ",\n"
             << "  \"all_inputs_k4_free\": true,\n"
             << "  \"all_inputs_independent5_free\": true,\n"
             << "  \"all_edge_deletions\": " << total_deletions << ",\n"
             << "  \"valid_deletions\": " << valid_deletions << ",\n"
             << "  \"output\": \"" << json_escape(options.output) << "\",\n"
             << "  \"filter\": "
                "\"independent-triple search in the deleted edge's common "
                "non-neighbourhood\",\n"
             << "  \"elapsed_seconds\": " << elapsed_seconds << "\n"
             << "}\n";
    if (!manifest) {
        throw std::runtime_error("failed writing manifest: " +
                                 options.manifest);
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
        std::ifstream input(options.input);
        if (!input) {
            throw std::runtime_error("cannot open input: " + options.input);
        }
        std::ofstream output(options.output);
        if (!output) {
            throw std::runtime_error("cannot open output: " + options.output);
        }

        const auto started = std::chrono::steady_clock::now();
        std::uint64_t input_records = 0;
        std::uint64_t total_deletions = 0;
        std::uint64_t valid_deletions = 0;
        std::string record;
        while (std::getline(input, record)) {
            const std::uint64_t line_number = input_records + 1;
            Graph graph = decode_graph6(record, line_number);
            if (edge_count(graph) != kInputEdges) {
                throw std::runtime_error(
                    "line " + std::to_string(line_number) +
                    ": expected 113 edges");
            }
            if (has_clique(graph, kAllVertices, 4)) {
                throw std::runtime_error("line " +
                                         std::to_string(line_number) +
                                         ": input contains K4");
            }
            if (has_independent_set(graph, 5)) {
                throw std::runtime_error(
                    "line " + std::to_string(line_number) +
                    ": input contains an independent 5-set");
            }

            for (int left = 0; left < kOrder; ++left) {
                for (int right = left + 1; right < kOrder; ++right) {
                    if (((graph[left] >> right) & 1U) == 0) {
                        continue;
                    }
                    ++total_deletions;
                    if (deletion_creates_independent_five(graph, left,
                                                          right)) {
                        continue;
                    }

                    graph[left] &= ~(std::uint32_t{1} << right);
                    graph[right] &= ~(std::uint32_t{1} << left);
                    output << encode_graph6(graph) << '\n';
                    graph[left] |= std::uint32_t{1} << right;
                    graph[right] |= std::uint32_t{1} << left;
                    ++valid_deletions;
                }
            }

            ++input_records;
            if (!options.quiet && input_records % 5000 == 0) {
                std::cerr << "checked " << input_records << " inputs; "
                          << valid_deletions << " valid deletions\n";
            }
        }
        if (!input.eof()) {
            throw std::runtime_error("failed while reading input: " +
                                     options.input);
        }
        output.close();
        if (!output) {
            throw std::runtime_error("failed writing output: " +
                                     options.output);
        }

        const double elapsed_seconds =
            std::chrono::duration<double>(std::chrono::steady_clock::now() -
                                          started)
                .count();
        write_manifest(options, input_records, total_deletions,
                       valid_deletions, elapsed_seconds);
        std::cerr << "inputs=" << input_records
                  << " all_deletions=" << total_deletions
                  << " valid_deletions=" << valid_deletions
                  << " elapsed_seconds=" << std::fixed << std::setprecision(3)
                  << elapsed_seconds << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
