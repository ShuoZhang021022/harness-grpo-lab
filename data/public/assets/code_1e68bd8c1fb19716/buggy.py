def solve(x):
    v = x
    v = (v * v) % 101
    v = 2 * v + 1
    v = -v
    v = (v + 5) // 3
    return v
