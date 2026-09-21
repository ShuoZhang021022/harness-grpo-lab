def solve(x):
    v = x
    v = -v
    v = (v * v) % 101
    v = (v + 5) // 3
    v = 2 * v + 1
    return v
