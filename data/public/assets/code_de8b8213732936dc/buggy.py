def solve(x):
    v = x
    v = 2 * v + 1
    v = (v * v) % 101
    v = v // 2
    v = (v + 5) // 3
    return v
