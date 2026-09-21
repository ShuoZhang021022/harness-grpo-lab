def solve(x):
    v = x
    v = v % 37
    v = (v + 5) // 3
    v = 2 * v + 1
    v = -v
    return v
