# -*- coding: utf-8 -*-
"""
Created on Wed Jun 21 15:58:35 2023

@author: Adith
"""

import os
import pandas as pd
import streamlit as st
import pickle
import warnings
warnings.filterwarnings("ignore")
import re
import nltk
from nltk.tokenize import word_tokenize
import spacy
from nltk.corpus import stopwords
from spacy.matcher import Matcher
import docx2txt
import PyPDF2
from transformers import TFT5ForConditionalGeneration, T5Tokenizer
from keybert import KeyBERT
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer
#import tempfile
import io
import tempfile
import subprocess
from docx import Document
import docx
from docx.api import Document




nltk.data.path.append("C:/Users/INDIA/AppData/Roaming/nltk_data")
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('vader_lexicon')
nltk.download('averaged_perceptron_tagger')
nltk.download('movie_reviews')
nltk.download('punkt')
nltk.download('conll2000')
nltk.download('brown')
my_stop_words = set(stopwords.words("english"))
warnings.filterwarnings('ignore', message='X does not have valid feature names')


  
st.set_option('deprecation.showPyplotGlobalUse', False)

pd.set_option('display.max_columns', None)  # To display all columns
pd.set_option('display.expand_frame_repr', True)  # To expand the DataFrame width
pd.set_option('display.max_colwidth', None)



#cleaning the corpus with regex library
def process_resume(resume_text):
    resume_text = re.sub('[%s]' % re.escape("""!"#$%&'()*+,-/:;<=>?@[\]^_`{|}~ """), ' ', resume_text)  # remove punctuation
    #resumeText = re.sub(r'[0-9]+', ' ', resumeText)  # remove numbers
    resume_text = re.sub(r'[^\x00-\x7f]', ' ', resume_text)  # remove non-ascii characters
    #resume_text = re.sub('\s+', ' ', resume_text)  # remove extra white space
    resume_text = re.sub('https?://\S+|www|WWW\.\S+', ' ', resume_text)  # remove URL words
    pattern = r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]'
    resume_text = re.sub(pattern, '', resume_text)
    resume_text = re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', resume_text)#add gaps between words
    resume_text = re.sub('⇨', ' ', resume_text)  # remove symbols
    resume_text = re.sub('\n',' ', resume_text)  # remove all newline characters
    return resume_text.lower()

#removing emojis from the dataframe
def remove_emoji(resume_text):
    emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"  # emoticons
                           u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                           u"\U0001F680-\U0001F6FF"  # transport & map symbols
                           u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           u"\U00002702-\U000027B0"
                           u"\U000024C2-\U0001F251"
                           "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', resume_text)


#extracting name from the given resume 
# from spacy.matcher import Matcher
# load pre-trained model
nlp = spacy.load('en_core_web_sm')

# initialize matcher with a vocab
matcher = Matcher(nlp.vocab)

    

loaded_model = pickle.load(open("final_model.sav",'rb'))
loaded_vect = pickle.load(open("tfidf_vec.sav",'rb'))
page = st.sidebar.radio("navigate",("Resume classification","Resume Screening"))
with st.container():
    st.header("Resume Parser App")
    st.caption("Only for Workday Resume,SQL Resume,React Resume and Peoplesoft Resume")
    

st.markdown('<hr>', unsafe_allow_html=True)
st.sidebar.title("Input data") 


def convert_doc_to_docx(file):
    if file.name.endswith('.docx'):
        text = docx2txt.process(file)
        return text
    elif file.name.endswith('.doc'):
        # Converting .doc file to .docx
        doc_file = file.name
        docx_file = doc_file + 'x'

        # Save the uploaded .doc file as .docx using python-docx
        with open(docx_file, 'wb') as f:
            f.write(file.read())

        # Read the converted .docx file
        encodings = ['utf-8', 'latin-1', 'cp1254']  # Specify the encodings to try
        for encoding in encodings:
            try:
                with open(docx_file, encoding=encoding) as f:
                    text = f.read()
                break
            except UnicodeDecodeError:
                continue
        else:
            print(f'Error: Unable to decode the file using supported encodings: {encodings}')
            text = ''

        # Remove the temporary .docx file
        os.remove(docx_file)

        return text
    else:
        print('Error: Unsupported file format')
        return ''



#extracting name from the given resume 
# from spacy.matcher import Matcher
# load pre-trained model
nlp = spacy.load('en_core_web_sm')

# initialize matcher with a vocab
matcher = Matcher(nlp.vocab)

nlp = spacy.load('en_core_web_sm')

def extract_name_from_resume(resume_text):
    nlp = spacy.load("en_core_web_sm")

    # First name and Last name are always Proper Nouns
    pattern = [{'POS': 'PROPN'}, {'POS': 'PROPN'}]

    matcher = Matcher(nlp.vocab)
    matcher.add('NAME', [pattern])

    matches = matcher(nlp(resume_text))

    if matches:
        for match_id, start, end in matches:
            span = nlp(resume_text)[start:end]
            return span.text
    else:
        pattern = r"(?i)\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b"
        match = re.search(pattern, resume_text)
        if match:
            name = match.group(1)
            return name.strip()
        else:
            return None



#extracting skills from the corpus 
nlp = spacy.load('en_core_web_sm')
def extract_skills(resume_text):
    nlp_text = nlp(resume_text)
 # removing stop words and implementing word tokenization
    tokens = [token.text for token in nlp_text if not token.is_stop]
    skills = ['workday', 'hcm', 'eib', 'picof','workday hcm',
              'workday studio','nnbound/outbound integrations',
              'peoplesoft', 'pia','ccb','birt','peci','ccw','pum','people tools',
              'peoplesoft implementation','peoplesoft components',
              'peoplesoft dba','peoplesoft admin','peoplesoft admin/dba','peopleSoft fscm', 
              'peopletoolsupgrade','peopletools upgrade','process scheduler servers',
              'peoplesoft hrms','peopleSoft consultant','peopledoft cloud',
              'PeopleSoft migrations','peoplesoft Testing Framework','pure internet architecture',
              'sql','sql server', 'ms sql server','msbi', 'sql developer', 'ssis','ssrs',
              'ssms','t-sql','tsql','Razorsql', 'razor sql','triggers','powerbi','power bi',
              'oracle sql', 'pl/sql', 'pl\sql','oracle', 'oracle 11g','oledb','cte','ddl',
              'dml','etl','mariadb','maria db','reactjs', 'react js', 'react js developer', 'html', 
              'css3','xml','javascript','html5','boostrap','jquery', 'redux','php', 'node js',
              'nodejs','apache','netbeans','nestjs','nest js','react developer','react hooks',
              'jenkins','rdbms','core connectors','PICOF','workday web services']

    skillset = []
    
    # check for one-grams (example: python)
    for token in tokens:
        if token.lower() in skills:
            skillset.append(token)
    
    # check for bi-grams and tri-grams (example: machine learning)
    for token in nlp_text.noun_chunks:
        token = token.text.lower().strip()
        if token in skills:
            skillset.append(token)
    
    return ",".join([i.capitalize() for i in set([i.lower() for i in skillset])])

#defining the function for resume summarization
def extract_resume_summary(resume_text, max_length=100):
    my_model = TFT5ForConditionalGeneration.from_pretrained('t5-small')
    tokenizer = T5Tokenizer.from_pretrained('t5-small')
    
    text = "summarize: " + resume_text
    input_ids = tokenizer.encode(text, return_tensors='pt', max_length=512, truncation=True)
    
    summary_ids = my_model.generate(input_ids, max_length=max_length, num_beams=4, no_repeat_ngram_size=2)
    t5_summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    
    return t5_summary
@st.cache(allow_output_mutation=True)
def load_model():
    model = KeyBERT("distilbert-base-nli-mean-tokens")
    return model
model = load_model()

def extract_keywords(resume):
    keywords_scores = model.extract_keywords(
    resume,
    top_n=10,
    keyphrase_ngram_range=(1, 3),
    use_maxsum = True,
    stop_words="english",)
    keywords = [keyword for keyword, _ in keywords_scores]
    return ",".join (keywords)
#extracting resume match using cosine similiarties
def get_resume_score(text):
    cv = CountVectorizer(stop_words='english')
    count_matrix = cv.fit_transform(text)
    #Print the similarity scores
   # print("\nSimilarity Scores:")
     
    #get the match percentage
    matchPercentage = cosine_similarity(count_matrix)[0][1] * 100
    matchPercentage = round(matchPercentage, 2)# round to two decimal
    return str(round( matchPercentage ))+ " % "



#extarcting experience details
def expDetails(text):
    text = text.lower()
    text = text.split()

    for i in range(len(text) - 2):
       if text[i] == 'year' or text[i] == 'years' or text[i] == 'year(s)':
            exp_text = ' '.join(text[i - 2: i + 3])
            matches = re.findall(r'\d+\.?\d*', exp_text)
            if len(matches) > 0:
                experience = float(matches[0])
                if 'month' in exp_text:
                    return experience
                else:
                    return str(round(experience*12 )) + " Months " 

    return None

#extracting education details from the resume
nlp = spacy.load('en_core_web_sm')

def parse_resume(resume_text):
    doc = nlp(resume_text)

    # Initialize variables to store education information
    education = []

    # Define education keywords
    education_keywords = ['education', 'qualification', 'academic background','university','school','college','degree','engineering','educational qualification']

    # Iterate over each sentence in the resume
    for sent in doc.sents:
        lower_sent = sent.text.lower()

        # Check if the sentence contains any education keywords
        if any(keyword in lower_sent for keyword in education_keywords):
            # Extract the entities in the sentence
            for ent in sent.ents:
                # Check if the entity label is related to education
                if ent.label_ in ['ORG', 'NORP']:
                    education.append(ent.text)

    return ",".join(education)


if page == "Resume classification":
    st.markdown("Overview")
   
    st.write("This app extracts information from your resume and gives you an idea about how well your resume matches to the description of job portals, the idea is to classify resume according to the category")
    st.markdown('<hr>', unsafe_allow_html=True)
    classify = st.sidebar.button("classify")
    
    def main():
       st.sidebar.error("Supports DOCX, DOC, PDF, TXT")
       uploaded_files = st.sidebar.file_uploader("Upload resumes", accept_multiple_files=True,type=['.doc','.docx','.pdf','.txt'])
    
       if uploaded_files:
        all_text = []
        
        for file in uploaded_files:
            text = convert_doc_to_docx(file)
            if text:
                all_text.append(text)
    
        # Output the number of resumes and their indices
        #st.write("Number of Resumes:", len(all_text))
        #st.write("Resume Indices:")
        #for i, text in enumerate(all_text):
            #st.write(f"Resume {i+1}:")
            #st.write(text)
        
            predictions = []  # List to store the predictions
            names = []
            name_list = []
            category_list = []
    
        if classify:
            for resume_text in all_text:
                cleaned_resume = process_resume(resume_text)
                cleaned_resume = remove_emoji(cleaned_resume)
                cleaned_resume = word_tokenize(cleaned_resume)
                my_stop_words = stopwords.words('english')
                cleaned_resume = [word for word in cleaned_resume if not word in my_stop_words]
                nlp = spacy.load('en_core_web_sm')
                cleaned_resume = nlp(' '.join(cleaned_resume))
                cleaned_resume = [token.lemma_ for token in cleaned_resume]
                cleaned_resume = ' '.join(cleaned_resume)
                #st.write(cleaned_resume)
    
                input_feat = loaded_vect.transform([cleaned_resume])
                prediction_id = loaded_model.predict(input_feat)[0]
                predictions.append(prediction_id)
    
                # Mapping resumes to given categories
                category_mapping = {
                    0: 'peoplesoft developers',
                    1: 'React developers',
                    2: 'SQL developers',
                    3: 'Workday resumes',
                }
                name = extract_name_from_resume(cleaned_resume)
                names.append(name)
    
            # Output the predictions for each resume
            for i, (prediction_id, name) in enumerate(zip(predictions, names)):
                category_name = category_mapping.get(prediction_id, "unknown")
                name_list.append(name)
                category_list.append(category_name)
    
            # Create a dataframe from the lists
            data = {'Name': name_list, 'Category': category_list}
            df = pd.DataFrame(data)
    
            # Display the dataframe in Streamlit
            st.write(df)
            
    if __name__ == "__main__":
                 main()           

if page == "Resume Screening":
    screening = st.sidebar.button("Screening")
    def main():
    
        st.sidebar.error("Supports DOCX, DOC, PDF, TXT")
        uploaded_files = st.sidebar.file_uploader("Upload resumes", accept_multiple_files=True)
        job_description = st.sidebar.text_input("Enter job description to know resume Match",placeholder="Paste Job Description")
        
        if uploaded_files:
            all_text = []
            
            for file in uploaded_files:
                text = convert_doc_to_docx(file)
                if text:
                    all_text.append(text)
            if screening:
                names = []
                skills = []
                educations = []
                experiences = []
                keywords = []
                scores = []
                summaries = []
                for resume_text in all_text:
                    
                     cleaned_resume = process_resume(resume_text)
                     cleaned_resume = remove_emoji(cleaned_resume)
                     cleaned_resume = word_tokenize(cleaned_resume)
                     my_stop_words = stopwords.words('english')
                     cleaned_resume = [word for word in cleaned_resume if not word in my_stop_words]
                     nlp = spacy.load('en_core_web_sm')
                     cleaned_resume = nlp(' '.join(cleaned_resume))
                     cleaned_resume = [token.lemma_ for token in cleaned_resume]
                     cleaned_resume = ' '.join(cleaned_resume)
                     #st.write(cleaned_resume)
                     name = extract_name_from_resume(cleaned_resume)
                     names.append(name)
                     skill = extract_skills(cleaned_resume)
                     skills.append(skill)
                     education = parse_resume(cleaned_resume)
                     educations.append(education)
                     experience = expDetails(cleaned_resume)
                     experiences.append(experience)
                     keyword = extract_keywords(cleaned_resume)
                     keywords.append(keyword)
                     corpus = [cleaned_resume,job_description]
                     score = get_resume_score(corpus)
                     scores.append(score)
                     summary = extract_resume_summary(cleaned_resume)
                     summaries.append(summary)
                     name_list = []
                     skill_list = []
                     education_list = []
                     experience_list = []
                     keyword_list = []
                     score_list = []
                     summary_list = []
                    
                for i,(skill,education,experience,keyword,score,name,summary)in enumerate(zip(skills,educations,experiences,keywords,scores,names,summaries)):
                    name_list.append(name)
                    skill_list.append(skill)
                    education_list.append(education)
                    experience_list.append(experience)
                    keyword_list.append(keyword)
                    score_list.append(score)
                    summary_list.append(summary)
                #create dataframe
                data_scr = {'Name': name_list,'Skills':skill_list,'Education':education_list,'Experience':experience_list,'Keywords':keyword_list,'Summary':summary_list,'Resume Match (in %)':score_list}
                df_scr = pd.DataFrame(data_scr)
                st.table(df_scr)
                
                #adding download button
                csv = df_scr.to_csv(index=False)
                st.download_button(label="Download",data=csv,file_name="Resume_data.csv")
                
           
            
            
                
               
                    
                            
            
                    
            
                   
       
       
       
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    
    if __name__ == "__main__":
         main() 
        
    
