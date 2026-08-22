// Exhaustive one-vertex extensions for Ramsey(4,5) graphs.
//
// If H is a Ramsey(4,5,n-1,e-d) graph, adding a new vertex v with
// neighbourhood S gives a Ramsey(4,5,n,e) graph iff
//   (1) H[S] is triangle-free, and
//   (2) S meets every independent 4-set of H.
// For --minimum-root we additionally require every old vertex to have
// final degree at least d, so v is a minimum-degree vertex.
//
// This program deliberately uses transparent exhaustive subset iteration.
// It emits every labelled extension; nauty shortg is used separately to
// canonically remove isomorphs.

#include <algorithm>
#include <bit>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using Mask = std::uint32_t;

struct Graph {
  int n = 0;
  std::vector<Mask> adj;
};

struct Options {
  std::string input;
  std::string output;
  int degree = -1;
  int expected_edges = -1;
  bool minimum_root = false;
  bool count_only = false;
  bool validate_inputs = true;
  bool validate_outputs = true;
};

[[noreturn]] void usage(const char* argv0) {
  std::cerr
      << "Usage: " << argv0
      << " --input FILE --degree D [--edges E] [--output FILE]\n"
      << "       [--minimum-root] [--count-only] [--no-input-validation]\n"
      << "       [--no-output-validation]\n";
  std::exit(2);
}

Options parse_options(int argc, char** argv) {
  Options o;
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    auto value = [&](const char* name) -> std::string {
      if (i + 1 >= argc) {
        throw std::runtime_error(std::string("missing value for ") + name);
      }
      return argv[++i];
    };
    if (a == "--input") o.input = value("--input");
    else if (a == "--output") o.output = value("--output");
    else if (a == "--degree") o.degree = std::stoi(value("--degree"));
    else if (a == "--edges") o.expected_edges = std::stoi(value("--edges"));
    else if (a == "--minimum-root") o.minimum_root = true;
    else if (a == "--count-only") o.count_only = true;
    else if (a == "--no-input-validation") o.validate_inputs = false;
    else if (a == "--no-output-validation") o.validate_outputs = false;
    else usage(argv[0]);
  }
  if (o.input.empty() || o.degree < 0 || o.degree > 21) usage(argv[0]);
  if (!o.count_only && o.output.empty()) {
    throw std::runtime_error("--output is required unless --count-only is set");
  }
  return o;
}

Graph decode_graph6(const std::string& raw) {
  std::string s = raw;
  if (!s.empty() && s.back() == '\r') s.pop_back();
  constexpr const char* header = ">>graph6<<";
  if (s.rfind(header, 0) == 0) s.erase(0, 10);
  if (s.empty()) throw std::runtime_error("empty graph6 record");
  const unsigned c0 = static_cast<unsigned char>(s[0]);
  if (c0 < 63 || c0 > 125 || c0 == 126) {
    throw std::runtime_error("only graph6 records with n <= 62 are supported");
  }
  Graph g;
  g.n = static_cast<int>(c0 - 63);
  if (g.n > 31) throw std::runtime_error("bit-mask implementation needs n <= 31");
  g.adj.assign(g.n, 0);

  std::size_t pos = 1;
  int bit = 5;
  auto next_bit = [&]() -> int {
    if (pos >= s.size()) throw std::runtime_error("truncated graph6 record");
    const unsigned char c = static_cast<unsigned char>(s[pos]);
    if (c < 63 || c > 126) throw std::runtime_error("invalid graph6 byte");
    const int answer = ((c - 63) >> bit) & 1;
    if (--bit < 0) {
      bit = 5;
      ++pos;
    }
    return answer;
  };
  for (int j = 1; j < g.n; ++j) {
    for (int i = 0; i < j; ++i) {
      if (next_bit()) {
        g.adj[i] |= Mask{1} << j;
        g.adj[j] |= Mask{1} << i;
      }
    }
  }
  return g;
}

std::string encode_graph6(const Graph& g) {
  if (g.n < 0 || g.n > 62) throw std::runtime_error("graph6 encoder needs n <= 62");
  std::string out;
  out.push_back(static_cast<char>(g.n + 63));
  int value = 0;
  int used = 0;
  auto push_bit = [&](int b) {
    value = (value << 1) | b;
    if (++used == 6) {
      out.push_back(static_cast<char>(value + 63));
      value = 0;
      used = 0;
    }
  };
  for (int j = 1; j < g.n; ++j) {
    for (int i = 0; i < j; ++i) push_bit((g.adj[i] >> j) & 1U);
  }
  if (used) {
    value <<= (6 - used);
    out.push_back(static_cast<char>(value + 63));
  }
  return out;
}

int edge_count(const Graph& g) {
  std::uint64_t sum = 0;
  for (Mask a : g.adj) sum += std::popcount(a);
  return static_cast<int>(sum / 2);
}

bool contains_clique_rec(const Graph& g, Mask candidates, int need) {
  if (need == 0) return true;
  if (std::popcount(candidates) < need) return false;
  while (candidates) {
    const int v = std::countr_zero(candidates);
    const Mask vb = Mask{1} << v;
    candidates ^= vb;
    if (contains_clique_rec(g, candidates & g.adj[v], need - 1)) return true;
    if (std::popcount(candidates) < need) return false;
  }
  return false;
}

bool contains_clique(const Graph& g, int k) {
  const Mask all = (Mask{1} << g.n) - 1;
  return contains_clique_rec(g, all, k);
}

Graph complement(const Graph& g) {
  Graph c{g.n, std::vector<Mask>(g.n)};
  const Mask all = (Mask{1} << g.n) - 1;
  for (int v = 0; v < g.n; ++v) c.adj[v] = (all ^ (Mask{1} << v)) & ~g.adj[v];
  return c;
}

bool is_ramsey_45(const Graph& g) {
  return !contains_clique(g, 4) && !contains_clique(complement(g), 5);
}

std::vector<Mask> triangles(const Graph& g) {
  std::vector<Mask> out;
  for (int a = 0; a < g.n; ++a) {
    for (int b = a + 1; b < g.n; ++b) {
      if (!(g.adj[a] & (Mask{1} << b))) continue;
      for (int c = b + 1; c < g.n; ++c) {
        if ((g.adj[a] & (Mask{1} << c)) && (g.adj[b] & (Mask{1} << c))) {
          out.push_back((Mask{1} << a) | (Mask{1} << b) | (Mask{1} << c));
        }
      }
    }
  }
  return out;
}

std::vector<Mask> independent_fours(const Graph& g) {
  std::vector<Mask> out;
  for (int a = 0; a < g.n; ++a) {
    for (int b = a + 1; b < g.n; ++b) {
      if (g.adj[a] & (Mask{1} << b)) continue;
      for (int c = b + 1; c < g.n; ++c) {
        const Mask abc = (Mask{1} << a) | (Mask{1} << b) | (Mask{1} << c);
        if ((g.adj[c] & abc) || (g.adj[b] & (Mask{1} << c))) continue;
        for (int d = c + 1; d < g.n; ++d) {
          if ((g.adj[d] & abc) == 0) out.push_back(abc | (Mask{1} << d));
        }
      }
    }
  }
  return out;
}

Graph extend(const Graph& h, Mask neighbourhood) {
  Graph g{h.n + 1, std::vector<Mask>(h.n + 1)};
  for (int v = 0; v < h.n; ++v) {
    g.adj[v] = h.adj[v];
    if (neighbourhood & (Mask{1} << v)) {
      g.adj[v] |= Mask{1} << h.n;
      g.adj[h.n] |= Mask{1} << v;
    }
  }
  return g;
}

bool next_same_popcount(Mask& x, Mask limit) {
  const Mask low = x & (~x + 1);
  const Mask ripple = x + low;
  if (ripple == 0 || ripple >= limit) return false;
  x = ripple | (((ripple ^ x) >> 2) / low);
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options o = parse_options(argc, argv);
    std::ifstream in(o.input);
    if (!in) throw std::runtime_error("cannot open input: " + o.input);
    std::ofstream output;
    if (!o.count_only) {
      output.open(o.output);
      if (!output) throw std::runtime_error("cannot open output: " + o.output);
    }

    const auto start = std::chrono::steady_clock::now();
    std::uint64_t records = 0;
    std::uint64_t subsets = 0;
    std::uint64_t extensions = 0;
    std::uint64_t rejected_independent4 = 0;
    std::uint64_t rejected_triangle = 0;
    std::uint64_t rejected_degree = 0;
    std::uint64_t total_i4 = 0;
    std::uint64_t total_triangles = 0;

    std::string line;
    while (std::getline(in, line)) {
      if (line.empty() || line == ">>graph6<<") continue;
      Graph h = decode_graph6(line);
      ++records;
      if (h.n >= 31) throw std::runtime_error("input order too large");
      if (o.degree > h.n) throw std::runtime_error("degree exceeds input order");
      if (o.validate_inputs && !is_ramsey_45(h)) {
        throw std::runtime_error("input record " + std::to_string(records) +
                                 " is not Ramsey(4,5)");
      }
      if (o.expected_edges >= 0 && edge_count(h) + o.degree != o.expected_edges) {
        throw std::runtime_error("wrong edge count in input record " +
                                 std::to_string(records));
      }

      const auto tris = triangles(h);
      const auto i4s = independent_fours(h);
      total_triangles += tris.size();
      total_i4 += i4s.size();

      Mask required = 0;
      Mask forbidden = 0;
      bool impossible_degree = false;
      if (o.minimum_root) {
        for (int v = 0; v < h.n; ++v) {
          const int dh = std::popcount(h.adj[v]);
          if (dh < o.degree - 1) impossible_degree = true;
          else if (dh == o.degree - 1) required |= Mask{1} << v;
          // A Ramsey(4,5) graph has maximum degree at most 13.
          if (dh >= 13) forbidden |= Mask{1} << v;
        }
      }
      if (impossible_degree || std::popcount(required) > o.degree ||
          (required & forbidden)) {
        continue;
      }

      const Mask limit = Mask{1} << h.n;
      Mask s = (Mask{1} << o.degree) - 1;
      bool more = true;
      while (more && s < limit) {
        ++subsets;
        if ((s & required) != required || (s & forbidden)) {
          ++rejected_degree;
          more = next_same_popcount(s, limit);
          continue;
        }
        bool ok = true;
        for (Mask q : i4s) {
          if ((s & q) == 0) {
            ok = false;
            ++rejected_independent4;
            break;
          }
        }
        if (ok) {
          for (Mask t : tris) {
            if ((s & t) == t) {
              ok = false;
              ++rejected_triangle;
              break;
            }
          }
        }
        if (ok) {
          Graph g = extend(h, s);
          if (o.validate_outputs) {
            if (!is_ramsey_45(g)) {
              throw std::runtime_error("internal error: invalid extension");
            }
            if (o.expected_edges >= 0 && edge_count(g) != o.expected_edges) {
              throw std::runtime_error("internal error: extension edge count");
            }
            if (o.minimum_root) {
              int mindeg = g.n;
              for (Mask a : g.adj) mindeg = std::min(mindeg, std::popcount(a));
              if (mindeg != o.degree) {
                throw std::runtime_error("internal error: root is not minimum");
              }
            }
          }
          ++extensions;
          if (!o.count_only) output << encode_graph6(g) << '\n';
        }
        more = next_same_popcount(s, limit);
      }
    }

    const double seconds = std::chrono::duration<double>(
                               std::chrono::steady_clock::now() - start)
                               .count();
    std::cerr << "records=" << records << " subsets=" << subsets
              << " extensions=" << extensions
              << " rejected_i4=" << rejected_independent4
              << " rejected_triangle=" << rejected_triangle
              << " rejected_degree=" << rejected_degree
              << " total_i4=" << total_i4
              << " total_triangles=" << total_triangles
              << " seconds=" << seconds << '\n';
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "error: " << e.what() << '\n';
    return 1;
  }
}
