import pandas as pd
import random
import os

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_path = os.path.join(base, 'data', '赋分后的高考模拟数据.csv')
output_path = os.path.join(base, 'data', '赋分后的高考模拟数据_with_sciences.csv')

print('读取', input_path)
df = pd.read_csv(input_path)

# 如果已有三科则跳过
required = ['物理原始','化学原始','生物原始','物理赋分','化学赋分','生物赋分']
if all(col in df.columns for col in required):
    print('数据已包含三科，跳过写入。')
else:
    random.seed(42)
    phys = []
    chem = []
    bio = []
    phys_f = []
    chem_f = []
    bio_f = []

    for _, row in df.iterrows():
        # 基于数学和英语生成三科原始分，带一点随机性 (物化生满分100分)
        math = row.get('数学', 80)
        eng = row.get('英语', 80)
        base_mean = (float(math) * 0.6 + float(eng) * 0.4) * 0.6  # 调整比例以适应100分满分
        p = int(max(0, min(100, round(base_mean + random.gauss(0, 8)))))
        c = int(max(0, min(100, round(base_mean + random.gauss(0, 8)))))
        b = int(max(0, min(100, round(base_mean + random.gauss(0, 8)))))

        # 简单赋分规则：赋分 = round(原始 * 0.8)（示例）
        pf = round(p * 0.8, 1)
        cf = round(c * 0.8, 1)
        bf = round(b * 0.8, 1)

        phys.append(p)
        chem.append(c)
        bio.append(b)
        phys_f.append(pf)
        chem_f.append(cf)
        bio_f.append(bf)

    df['物理原始'] = phys
    df['化学原始'] = chem
    df['生物原始'] = bio
    df['物理赋分'] = phys_f
    df['化学赋分'] = chem_f
    df['生物赋分'] = bio_f

    df.to_csv(output_path, index=False)
    print('写入完成:', output_path)
