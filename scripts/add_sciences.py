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

        # 赋分规则：赋分成绩从100分向下递减，所有科目赋分都在0-100分范围内
        pf = round(p * 1.0, 1)  # 物化生满分100分，直接使用原始分
        cf = round(c * 1.0, 1)
        bf = round(b * 1.0, 1)

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

    # 重新计算所有科目的赋分，确保都在0-100分范围内
    print('重新计算所有赋分列...')
    df['历史赋分'] = df['历史原始'].apply(lambda x: round(float(x) * (100/100), 1) if pd.notna(x) else 0)  # 假设历史满分100分
    df['地理赋分'] = df['地理原始'].apply(lambda x: round(float(x) * (100/100), 1) if pd.notna(x) else 0)  # 假设地理满分100分
    df['政治赋分'] = df['政治原始'].apply(lambda x: round(float(x) * (100/100), 1) if pd.notna(x) else 0)  # 假设政治满分100分

    df.to_csv(output_path, index=False)
    print('写入完成:', output_path)
