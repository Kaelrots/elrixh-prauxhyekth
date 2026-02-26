# AI 일러스트레이션 하이브리드 워크플로우 가이드

<font style="font-weight:bold">Gemini(나노바나나 Pro) × NovelAI × Photoshop</font>

이 문서는 Gemini의 뛰어난 언어 이해력/구성력과 NovelAI의 애니메이션 특화 캐릭터 생성 능력, 그리고 Photoshop의 정교한 편집 기능을 결합하여 최상의 결과물을 얻기 위한 작업 공정을 다룹니다.

## 📋 워크플로우 개요 (Workflow Overview)

1. <font style="font-weight:bold">기획 및 초안 (Gemini):</font> 자연어로 구상한 이미지를 시각화하고 구도(Layout)를 확정.
    
2. <font style="font-weight:bold">프롬프트 추출 (Gemini):</font> 확정된 초안을 NAI용 태그(Tag)로 변환.
    
3. <font style="font-weight:bold">캐릭터 생성 (NovelAI):</font> 태그를 활용해 캐릭터 리소스(소스) 생성. (배경 제거 용이성 확보)
    
4. <font style="font-weight:bold">배경 생성 (Gemini):</font> 고해상도 및 정교한 배경 리소스 생성.
    
5. <font style="font-weight:bold">합성 및 보정 (Photoshop):</font> 리소스 합성 및 톤 앤 매너 통일.
    

## 단계별 상세 가이드 (Step-by-Step)

### STEP 1. 기획 및 초안 제작 (Art Direction)

<font style="font-weight:bold">도구:</font> Gemini (나노바나나 Pro / Gemini 3 Pro Image)

추상적인 아이디어를 구체적인 시각 정보로 변환하는 단계입니다.

1. <font style="font-weight:bold">자연어 브레인스토밍:</font>
    
    - 캐릭터의 외형, 성격, 입고 있는 옷, 현재 상황, 배경 분위기 등을 줄글(자연어)로 설명합니다.
        
    - _예: "사이버펑크 도시의 뒷골목, 비가 내리고 있고, 은발의 소녀가 네온사인을 등진 채 경계하는 눈빛으로 서 있어."_
        
2. <font style="font-weight:bold">초안 생성 및 피드백 루프:</font>
    
    - Gemini가 생성한 이미지를 확인합니다.
        
    - 원하는 구도, 조명 방향, 포즈가 나올 때까지 피드백을 주고받으며 수정합니다. (예: "시선을 좀 더 위로 처리해 줘", "조명을 더 어둡게 해 줘")
        
3. <font style="font-weight:bold">청사진(Blueprint) 확정:</font>
    
    - 최종 합성에 참고할 '완벽한 구도'의 이미지를 선정합니다.
        

### STEP 2. NAI용 프롬프트 추출 (Prompt Engineering)

<font style="font-weight:bold">도구:</font> Gemini

Gemini가 생성한 초안의 시각적 요소를 NovelAI가 이해할 수 있는 단부루(Danbooru) 스타일 태그로 변환합니다.

1. <font style="font-weight:bold">요청:</font> "확정된 초안 이미지의 캐릭터 외형, 의상, 포즈를 NAI용 영문 태그로 추출해 줘."
    
2. <font style="font-weight:bold">검수:</font> 추출된 태그 중 불필요한 배경 묘사 태그는 제거하고, 캐릭터 핵심 태그만 남깁니다.
    

### STEP 3. 캐릭터 소스 생성 (Character Asset)

<font style="font-weight:bold">도구:</font> NovelAI (NAI)

애니메이션 화풍에 특화된 고품질 캐릭터 이미지를 생성합니다.

1. <font style="font-weight:bold">프롬프트 입력:</font> Gemini에게 받은 태그를 입력합니다.
    
2. <font style="font-weight:bold">배경 제거(누끼) 최적화 태그 추가:</font>
    
    - NAI는 완벽한 투명 배경 생성이 어렵습니다. 포토샵 작업을 위해 <font style="font-weight:bold">단색 배경</font>을 유도합니다.
        
    - <font style="font-weight:bold">권장 태그:</font> `simple background`, `white background` (또는 캐릭터 색과 대비되는 색), `flat color`
        
    - <font style="font-weight:bold">제외 태그:</font> `depth of field`, `bokeh`, `blurry background` (외곽선 흐림 방지)
        
3. <font style="font-weight:bold">생성 및 선별:</font> 여러 장(Batch)을 생성하여 표정과 디테일이 가장 좋은 컷을 선정합니다.
    

### STEP 4. 배경 소스 생성 (Background Asset)

<font style="font-weight:bold">도구:</font> Gemini (나노바나나 Pro)

캐릭터가 배치될 고해상도 배경을 생성합니다.

1. <font style="font-weight:bold">배경 전용 프롬프트:</font> STEP 1에서 사용한 프롬프트에서 캐릭터 묘사를 제외하고 배경 묘사를 강화합니다.
    
    - _팁: "Nobody, Scenery only" 등의 텍스트를 추가하여 인물 등장을 배제합니다._
        
2. <font style="font-weight:bold">옵션 설정:</font>
    
    - <font style="font-weight:bold">해상도:</font> 가능한 가장 높은 해상도 (4K 권장).
        
    - <font style="font-weight:bold">조명 일치:</font> STEP 1의 초안과 동일한 광원 방향과 분위기를 유지하도록 요청합니다.
        

### STEP 5. 합성 및 최종 완성 (Compositing)

<font style="font-weight:bold">도구:</font> Adobe Photoshop

준비된 리소스를 하나로 합칩니다.

1. <font style="font-weight:bold">레이어 배치:</font> 배경 이미지를 아래에, 캐릭터 이미지를 위에 배치합니다.
    
2. <font style="font-weight:bold">누끼 따기 (Masking):</font>
    
    - 캐릭터 레이어에서 '피사체 선택(Select Subject)' 또는 '마법봉(Magic Wand)'을 사용하여 단색 배경을 제거합니다.
        
    - 가장자리가 어색할 경우 `Select and Mask` 기능을 이용해 외곽선을 다듬습니다.
        
3. <font style="font-weight:bold">톤 앤 매너 보정 (Color Grading):</font>
    
    - 캐릭터가 배경에 붕 떠 보이지 않도록 <font style="font-weight:bold">커브(Curves)</font>나 <font style="font-weight:bold">레벨(Levels)</font>을 조정하여 명도와 대비를 배경에 맞춥니다.
        
    - 배경 색감을 캐릭터에 살짝 입히는(Color Balance) 작업을 통해 통일감을 줍니다.
        
4. <font style="font-weight:bold">마무리 효과:</font> 그림자 추가, 하이라이트 강조, 전체적인 노이즈/질감 추가 등을 수행합니다.
    

## 💡 핵심 팁 (Pro Tips)

- <font style="font-weight:bold">i2i (Image to Image) 활용:</font> NAI에서 원하는 포즈가 잘 안 나올 경우, Gemini가 만든 초안 이미지를 NAI의 i2i 소스로 넣고 `Denoising Strength`를 조절하면 구도를 유지한 채 화풍만 바꿀 수 있습니다.
    
- <font style="font-weight:bold">손/발 디테일 수정:</font> NAI가 손을 잘 못 그릴 경우, 포토샵의 '생성형 채우기(Generative Fill)'나 Gemini의 '부분 수정(Inpainting)' 기능을 활용해 교정합니다.
    
- <font style="font-weight:bold">해상도 차이:</font> NAI 출력물 해상도가 낮을 경우, 업스케일링(Upscaling) 툴(Waifu2x 등)을 한번 거친 후 포토샵으로 가져가는 것이 좋습니다.