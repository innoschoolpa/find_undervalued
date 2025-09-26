import pandas as pd

# CSV 파일 읽기
try:
    df = pd.read_csv('test_final.csv')
    
    # 컬럼명을 한국어로 변경
    df_display = df.copy()
    df_display.columns = ['종목코드', '종목명', '등급', '점수', '시총(억원)', '현재가', '52주위치(%)', 'PER', 'PBR', '섹터평가']
    
    # 숫자 포맷팅
    df_display['시총(억원)'] = df_display['시총(억원)'].apply(lambda x: f'{x:,.0f}억' if pd.notna(x) else 'N/A')
    df_display['현재가'] = df_display['현재가'].apply(lambda x: f'{x:,.0f}원' if pd.notna(x) else 'N/A')
    df_display['52주위치(%)'] = df_display['52주위치(%)'].apply(lambda x: f'{x:.1f}%' if pd.notna(x) else 'N/A')
    df_display['점수'] = df_display['점수'].apply(lambda x: f'{x:.1f}' if pd.notna(x) else 'N/A')
    df_display['PER'] = df_display['PER'].apply(lambda x: f'{x:.1f}' if pd.notna(x) else 'N/A')
    df_display['PBR'] = df_display['PBR'].apply(lambda x: f'{x:.1f}' if pd.notna(x) else 'N/A')
    
    # 순위 추가
    df_display = df_display.reset_index(drop=True)
    df_display.index = df_display.index + 1
    
    print('📊 종목 분석 결과')
    print('=' * 80)
    print(df_display.to_string(index=True))
    print('=' * 80)
    
    # 요약 통계
    print('\n📈 분석 요약:')
    print(f'• 총 분석 종목: {len(df)}개')
    print(f'• 평균 점수: {df["score"].mean():.1f}점')
    print(f'• 최고 점수: {df["score"].max():.1f}점 ({df.loc[df["score"].idxmax(), "name"]})')
    print(f'• 최저 점수: {df["score"].min():.1f}점 ({df.loc[df["score"].idxmin(), "name"]})')
    
    # 등급별 분포
    grade_counts = df['grade'].value_counts().sort_index()
    print('\n🏆 등급별 분포:')
    for grade, count in grade_counts.items():
        print(f'• {grade}등급: {count}개')
        
except Exception as e:
    print(f'오류 발생: {e}')

