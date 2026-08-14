rows = [
    ("echo", 7019, 2), ("echo", 7697, 2), ("delta", 7253, 1), ("foxtrot", 7718, 2),
    ("echo", 7667, 1), ("delta", 7405, 4), ("alpha", 7835, 2), ("delta", 7814, 1),
    ("echo", 7197, 4), ("foxtrot", 7438, 1), ("echo", 7322, 4), ("golf", 7127, 4),
    ("bravo", 7430, 1), ("golf", 7853, 2), ("charlie", 7649, 1), ("foxtrot", 7090, 4),
    ("golf", 7578, 1), ("hotel", 7294, 2), ("delta", 7677, 1), ("golf", 7997, 3),
    ("hotel", 7297, 2), ("bravo", 7144, 4), ("charlie", 7635, 3), ("echo", 7030, 2),
    ("bravo", 7350, 4), ("charlie", 7773, 1), ("golf", 7564, 4), ("foxtrot", 7725, 1),
    ("hotel", 7382, 2), ("charlie", 7100, 3), ("alpha", 7775, 1), ("charlie", 7075, 4),
    ("golf", 7321, 2), ("delta", 7982, 3), ("delta", 7222, 3), ("bravo", 7074, 3),
    ("echo", 7553, 1), ("echo", 7138, 4), ("charlie", 7671, 3), ("hotel", 7641, 2),
    ("delta", 7757, 1), ("echo", 7428, 4), ("bravo", 7013, 4), ("golf", 7698, 1),
    ("echo", 7325, 1), ("bravo", 7484, 1), ("charlie", 7236, 2), ("alpha", 7040, 2),
    ("alpha", 7474, 2), ("alpha", 7847, 3), ("golf", 7874, 2), ("hotel", 7915, 3),
    ("alpha", 7141, 4), ("echo", 7878, 4), ("delta", 7975, 1), ("alpha", 7760, 1),
    ("charlie", 7815, 3), ("bravo", 7196, 1), ("bravo", 7148, 2), ("delta", 7642, 3),
]
for i, (h, p, w) in enumerate(rows):
    print("shard-%03d,%s.example.com,%d,%d" % (i, h, p, w))
