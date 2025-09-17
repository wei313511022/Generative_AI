import google.generativeai as genai
import pandas as pd
import time
import re

genai.configure(api_key="AIzaSyALVYRXp9MdFyBCj5kJWsyyXesEMhlL9TI")
# AIzaSyALVYRXp9MdFyBCj5kJWsyyXesEMhlL9TI wei.c
# AIzaSyBJBsfK55YYQa4Kx-qOov52_dw2tPjTzeA tommy
model = genai.GenerativeModel("gemini-2.0-flash" )  # Use Gemini-pro model
# gemini-2.0-flash 15/min
# gemini-2.0-flash-lite 30/min

# Load dataset
input_file = "mmlu_submit.csv"
df = pd.read_csv(input_file)

example_file = "Example_Per_Task.csv"
df1 = pd.read_csv(example_file)

# Function to generate prompts

# def verify_prompt(question, choices, task, last_answer):
    
#     prompt = f"""
#     You are a professor in {task}. Your task is to check whether a student's answer to the following multiple-choice question is correct.
    
#     Question: {question}
    
#     Choices:
#     A) {choices[0]}
#     B) {choices[1]}
#     C) {choices[2]}
#     D) {choices[3]}
    
#     And his answer is {last_answer}.
    
#     Is this answer correct? If not, what is the right answer?

#     Select the most correct answer (A, B, C, or D) and respond with ONLY the letter.
#     """
#     return prompt.strip()

def generate_prompt(question, choices, task, example):
    """
    Creates a well-structured prompt for Gemini API.
    Modify for Few-Shot, Chain-of-Thought, etc.
    """
    prompt = f"""
    You are an AI expert in {task}. Assume you have searched the latest academic papers and expert sources.
    
    ## **Objective:**
    Your task is to **analyze and answer multiple-choice questions** based on {task} contexts. You will follow a structured approach to ensure logical accuracy.
    
    ---
    
    ## **Example Question:**
    {example}

    **Step 1: Gather Information**
    - If you were searching reliable sources, what key facts would you find?
    - Summarize the most important details relevant to this question.

    **Step 2: Analyze Each Answer Choice**
    - Compare the available choices using logical deduction.
    - Eliminate incorrect options with reasoning.

    **Step 3: Select the Most Correct Answer**
    - Justify why this answer is the best based on what is known.
    
    **Step 4: Provide the Final Answer**
    - Format your response as **Final Answer: [X]** (where X is A, B, C, or D).

    ## **Now, answer the following question:**

    **Question:** {question}

    **Choices:**
    A) {choices[0]}
    B) {choices[1]}
    C) {choices[2]}
    D) {choices[3]}

    Provide the best possible answer with a logical explanation.
    """
    return prompt.strip()

def call_gemini(prompt):
    """
    Calls Google Gemini API correctly using GenerativeModel.
    """
    try:
        response = model.generate_content(prompt)
        answer = response.text.strip()
        print(answer)
        match = re.search(r"\*\*Final Answer: \[([ABCD])\]\*\*", answer)
        
        if match:
            print(f"match [{match.group(1)}]")
            return match.group(1)
        # # Ensure output is A/B/C/D
        # if match in ["A", "B", "C", "D"]:
        #     return match
        else:
            match = re.search(r"\*\*Final Answer: ([ABCD])\*\*", answer)
            if match:
                print(f"match {match.group(1)}")
                return match.group(1)
            else:
                return answer # Default fallback (modify if needed)
    except Exception as e:
        print(f"Error: {e}")
        return "e"  # Default answer in case of API failure

# Predict answers
predictions = []
correct = 0
total = 0
for _, row in df.iterrows():
    
    total = total + 1
    question = row["input"]
    choices = [row["A"], row["B"], row["C"], row["D"]]
    # target = row["target"]
    task = row["task"]
    
    x = 0
    
    if task == "high_school_european_history":
        x = 2
    elif task == "high_school_us_history":
        x = 8
    elif task == "high_school_world_history":
        x = 9
    elif task == "high_school_microeconomics":
        x = 6
    elif task == "high_school_biology":
        x = 0
    elif task == "high_school_government_and_politics":
        x = 4
    elif task == "high_school_geography":
        x = 3
    elif task == "high_school_psychology":
        x = 7
    elif task == "high_school_computer_science":
        x = 1
    elif task == "high_school_macroeconomics":
        x = 5
    
    example = "\n" + df1.iloc[x,1] + "\nA: " + df1.iloc[x,2] + "\nB" +  df1.iloc[x,3] + "\nC" + df1.iloc[x,4] + "\nD" + df1.iloc[x,5] + "\nANSWER is " + df1.iloc[x,6]
        
    # Generate prompt
    prompt = generate_prompt(question, choices, task, example)
    
    print(prompt)
    
    # Get response from Gemini
    answer = call_gemini(prompt)
    
    # prompt = verify_prompt(question, choices, task, answer1)
    # answer = call_gemini(prompt)
    
    
    predictions.append([row["Unnamed: 0"], answer])
    print(row["Unnamed: 0"])
    # if row["Unnamed: 0"] == 41:
    #     break
    # if answer == target:
    #     correct = correct + 1
    #     print(f"correct: {answer}, {target}")
    # else:
    #     print(f"incorrect: {answer}, {target}")
    # Rate-limit API calls to avoid overloading
    time.sleep(4)

print(f"accuracy: {correct/total}")
# Save submission file
output_file = "test_output333.csv"
submission_df = pd.DataFrame(predictions, columns=["ID", "output"])
submission_df.to_csv(output_file, index=False)

print(f"Submission saved as {output_file}")


# 讀取 CSV 檔案
df111 = pd.read_csv("test_output333.csv")

# 處理第一欄，假設第一欄的名稱是 'Column1'
df111.iloc[:, 1] = df111.iloc[:, 1].astype(str).apply(lambda x: re.findall(r'[a-zA-Z]+', x)[-1] if re.findall(r'[a-zA-Z]+', x) else '')

# 儲存為新的 CSV 檔案
df111.to_csv("modified_file.csv", index=False)

print("處理完成，已儲存為 modified_file333.csv")