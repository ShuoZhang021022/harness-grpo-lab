# Initial Tool Library

50 Python tools with no LLM calls, network access, or execution of supplied Python source code.

The library contains 18 math tools, 17 code tools, and 15 life-scenario tools. See catalog.json for interface parameters and examples.

- `ast_structure` [code]: Return the complete Python AST as a structural string without source locations; never execute it.
- `binomial_coefficient` [math]: Compute exact n-choose-k for nonnegative integers, returning zero when k>n.
- `canonical_json` [code]: Parse JSON and serialize with sorted keys, UTF-8 characters, and compact separators; rejects NaN/Infinity.
- `chinese_remainder` [math]: Solve simultaneous congruences with pairwise coprime moduli>1; return least nonnegative solution.
- `compare_json` [code]: Recursively compare JSON values; distinguish types and return changed, added or removed paths.
- `compile_check` [code]: Compile Python without executing it; catches syntax and context errors such as return outside function.
- `enumerate_combinations` [math]: Enumerate positional k-combinations in input order; no deduplication or silent truncation.
- `enumerate_permutations` [math]: Enumerate positional length-k permutations; duplicate input values can produce duplicate outputs.
- `euclidean_distance` [life]: Compute straight-line Euclidean distance between equal-dimensional coordinate lists.
- `extended_gcd` [math]: Return integers gcd,x,y satisfying a*x+b*y=gcd>=0 (Bezout coefficients).
- `extract_lines` [code]: Extract an inclusive one-based line range, preserving line endings; reject out-of-range requests.
- `filter_places` [life]: Return place IDs whose explicit attributes equal every supplied constraint; missing fields do not match.
- `find_calls` [code]: List syntactic call expressions and line numbers; does not prove which calls execute at runtime.
- `find_definitions` [code]: List class, function and async-function definitions, including nested definitions and line ranges.
- `find_imports` [code]: List import statements syntactically without loading the referenced modules.
- `follow_relative_directions` [life]: Follow left/right/back turns and nonnegative forward distances; Cartesian x=east,y=north, headings N/E/S/W.
- `grid_shortest_path` [life]: Find four-neighbor shortest path on a rectangular grid; 0=free, 1=blocked; positions [row,column].
- `haversine_km` [life]: Approximate spherical distance in km for [latitude,longitude] degrees, radius=6371.0088 km; not route distance.
- `integer_gcd` [math]: Return the nonnegative greatest common divisor of a nonempty integer list.
- `integer_lcm` [math]: Return the nonnegative least common multiple of a nonempty integer list.
- `integer_square_root` [math]: Compute exact floor square root and square status for a nonnegative integer.
- `intersect_candidates` [life]: Intersect nonempty lists of candidate string IDs; return sorted unique IDs.
- `intersect_time_windows` [life]: Intersect closed time intervals in the caller's common numeric time unit; touching endpoints count, disjoint returns null.
- `is_prime` [math]: Test integer primality exactly using trial division; integers below 2 return false.
- `list_literals` [code]: List Python constant literals as repr strings and line numbers, including bytes and complex values.
- `manhattan_distance` [life]: Compute Manhattan (L1) distance between equal-dimensional coordinate lists.
- `modular_inverse` [math]: Return modular multiplicative inverse; fail if modulus<=1 or inverse does not exist.
- `modular_power` [math]: Compute base**exponent modulo a positive modulus; exponent must be nonnegative.
- `multinomial_coefficient` [math]: Count arrangements with the supplied nonnegative category counts.
- `name_usage` [code]: Count AST Name loads/stores/deletes by spelling; does not resolve lexical scopes or attributes.
- `nearest_places` [life]: Rank supplied places by Euclidean distance from origin; break ties by string ID; return up to k places.
- `parse_python` [code]: Parse Python syntax and return top-level AST node types, or syntax error details.
- `point_in_rectangle` [life]: Test membership in a closed axis-aligned rectangle [xmin,ymin,xmax,ymax], including the boundary.
- `polynomial_evaluate` [math]: Evaluate exact rational coefficients in descending power order; return a fraction string.
- `positive_divisors` [math]: Return all positive divisors of a positive integer in ascending order.
- `prime_factorization` [math]: Factor a positive integer into [prime, exponent] pairs by exact trial division.
- `python_tokens` [code]: Tokenize Python source, retaining comments but omitting newline, indentation and end-marker tokens.
- `quadratic_roots` [math]: Return two approximate complex roots as [real,imaginary] pairs; requires nonzero a.
- `rational_arithmetic` [math]: Apply add/subtract/multiply/divide to exact fraction strings; return a reduced fraction string.
- `reachable_nodes` [life]: Return nodes reachable by directed edges, including start, in breadth-first discovery order.
- `rename_name_nodes` [code]: Rename matching AST Name nodes only; NOT scope-aware, and does not rename parameters or attributes. Reformats code.
- `replace_lines` [code]: Replace an inclusive one-based line range verbatim; caller supplies replacement newlines.
- `replace_number_literals` [code]: Replace numeric AST constants, excluding booleans; validate count. Negative signs are separate AST nodes. Reformats code.
- `replace_text_exact` [code]: Replace all literal occurrences only if their number exactly matches expected_count; fail otherwise.
- `resolve_place_name` [life]: Resolve exact case-insensitive names/aliases after trimming whitespace. Return all matching IDs; never guess ambiguity.
- `shortest_unweighted_path` [life]: Find a shortest directed unweighted path by BFS. Neighbors are node-ID lists; unreachable returns null.
- `shortest_weighted_path` [life]: Dijkstra on directed node->{neighbor:nonnegative finite weight} graphs with string IDs; unreachable returns null.
- `solve_linear_system` [math]: Solve a square nonsingular system exactly over rational numbers; reject singular systems.
- `topological_order` [life]: Topologically sort a directed dependency graph with string IDs; lexical tie-breaking, reject cycles.
- `unified_diff` [code]: Produce a unified diff of two in-memory texts using fixed before/after filenames.
