

# 逐行读取openalex_year.csv
year_data = {}
with open('/home/1900016622_kd/openalex_202506/openalex_year.csv', 'r') as f:
    next(f)  # 跳过表头
    for line in f:
        paper_id, year = line.strip().split('\t')
        year_data[paper_id] = int(year)

# 逐行读取openalex_fields.csv

topic_subfield = {}
with open('/home/1900016622_kd/openalex_202506/topics.tsv', 'r', encoding='utf-8') as file:
    header = file.readline().strip().split('\t')
    for line in file:
        values = line.strip().split('\t')
        if values==['']:
            continue
        topic_id = values[header.index('id')][21:]
        topic_subfield[topic_id] = values[header.index('subfield_display_name')]





field_data = {}
with open('/home/1900016622_kd/openalex_202506/openalex_topics.csv', 'r') as f:
    next(f)  # 跳过表头
    for line in f:
        paper_id, field_id = line.strip().split('\t')
        if paper_id not in field_data:
                field_data[paper_id] = set()
        field_data[paper_id].add(topic_subfield[field_id])

# 逐行读取openalex_c5.csv
c5_data = {}
with open('openalex_c5.csv', 'r') as f:
    next(f)  # 跳过表头
    for line in f:
        paper_id, c5 = line.strip().split('\t')
        c5_data[paper_id] = float(c5)

# 计算每年每领域的平均C5
field_year_c5_sum = {}
field_year_count = {}
for paper_id in c5_data:
    if paper_id in year_data and paper_id in field_data:
        year = year_data[paper_id]
        fields = field_data[paper_id]
        c5 = c5_data[paper_id]
        for field in fields:
            field_year = (year, field)
            if field_year not in field_year_c5_sum:
                field_year_c5_sum[field_year] = 0
                field_year_count[field_year] = 0
            field_year_c5_sum[field_year] += c5
            field_year_count[field_year] += 1

# 计算每年每领域的平均C5
field_year_avg_c5 = {}
for field_year in field_year_c5_sum:
    field_year_avg_c5[field_year] = field_year_c5_sum[field_year] / field_year_count[field_year]

# 计算每篇文章的标准化C5
results = []
for paper_id in c5_data:
    if paper_id in year_data and paper_id in field_data:
        year = year_data[paper_id]
        fields = field_data[paper_id]
        c5 = c5_data[paper_id]
        for field in fields:
            field_year = (year, field)
            if field_year in field_year_avg_c5:
                avg_c5 = field_year_avg_c5[field_year]
                c5_norm = c5 / avg_c5  # 标准化
                results.append((paper_id, year, field, c5, avg_c5, c5_norm))

# 输出或保存结果
with open('openalex_normalized_c5_results.csv', 'w') as f:
    f.write('paper_id\tc5_norm\n')
    for result in results:
        f.write(f'{result[0]}\t{result[5]}\n')

print("标准化C5计算完成，结果已保存到 'standardized_c5_results.csv'。")
