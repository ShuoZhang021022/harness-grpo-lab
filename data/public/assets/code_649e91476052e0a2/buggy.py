def solve(x):
    v = x
    v = v // 2
    v = (v + 5) // 3
    v = v % 37
    v = 2 * v + 1
    return v
