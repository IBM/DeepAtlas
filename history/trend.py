from matplotlib import pyplot as plt
plt.style.use('ggplot')

xs, ys = [], []
with open('./multiTimeline (1).csv', 'r') as f:
    for line in f.readlines():
        line = line.strip().split(',')
        xs.append(line[0])
        ys.append(int(line[1]))

plt.figure(figsize=(4, 3), dpi=150)
plt.plot(ys)
plt.title('Google Trend')
plt.ylabel('Interest')
plt.xticks(range(0, len(ys), 12), ['' for _ in range(0, len(ys), 12)])
plt.xlim([0, len(ys)])
plt.ylim([0, 100])
plt.tight_layout()
plt.show()