def solve(x):
    v = x
    v = (v + 5) // 3
    v = v % 37
    v = (v * v) % 101
    v = v + 7
    return v
