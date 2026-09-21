def solve(x):
    v = x
    v = (v + 5) // 3
    v = 2 * v + 1
    v = v // 2
    v = (v * v) % 101
    return v
