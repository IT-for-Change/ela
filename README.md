<img src="https://github.com/IT-for-Change/ela/blob/main/ela/public/ela_logo_192x.png" alt="The ELA Logo">

### ELA

ELA is non-generative AI-driven learning assessment software.

ELA comprises the following components (with their github repositories linked)
* [ELA AI](https://github.com/IT-for-Change/elaai), the AI engine
* [ELA Collect](https://github.com/IT-for-Change/ela_collect), an Android mobile application for teachers to capture learner outputs in the classroom. This is a forked customization of the renowned [ODK Collect](https://github.com/getodk/collect) app.
* [ELA Web](https://github.com/IT-for-Change/ela), a browser-based web application for teachers to control the entire assessment process
* [ELA Middleware](https://github.com/IT-for-Change/elamid), a technical component hidden from users that orchestrates interactions between ELA Web and ELA AI to reduce computer resource usage.

A companion component is the [ECUBE data collector](https://github.com/IT-for-Change/ecube-data-collection), a custom data collection tool that extracts learner outputs from the ECUBE English Language Lab (ELL) software developed by KITE. Read more about KITE [here](https://kite.kerala.gov.in) and the ECUBE ELL [here](https://ecube.kite.kerala.gov.in)

### Technical documentation
See here for technical documentation and user guide.

### Principles

- **Pedagogy Driven**  : Designed by educators and technologists at [IT for Change](https://itforchange.net), ELA is driven by pedagogy, not technology.
- **Teacher First**    : ELA is teacher-facing software. No learner <-> computer/phone interaction is necessary for the learning process.
- **Offline First**    : ELA is carefully architected to run on a desktop computer. No internet required.
- **Privacy Focus**    : With no internet required, all learner data and assessment reports stay on the computer. No data is shared or visible to any party, including the app developer.
- **Openness**         : ELA is licensed to be free and open source (FOSS). Always.
  

### What is 'ELA'
- 'ELA' is a polysemous acronym. That is, an acronym with multiple, related meanings.
- Language learning assessment is central to the software, and the English language in particular. ELA is therefore 'English Language Assessment'.
- In the immediate roadmap is support for other languages (Indian languages, to begin with). Here, ELA is therefore also 'E Language Assessment', the 'E' stands for 'Electronic' of course. 
- A future iteration of the software will also support other forms of assessments based on non-speech inputs such as MCQs that the teacher will record based on learner responses, and OCR scans of paper-based MCQ responses of learners etc. This could be in any subject of learning. Here, ELA is 'E Learning Assessment'. Note the absence of a hyphen between 'E' and 'Learning'. This is not 'E-Learning'. Learning happens in the classroom.
- Lastly, in homage to the Free Software Movement and The GNU Project, ELA is of course also a recursive acronym that expands to **ELA Learning Assessment**
  

### Software features
- Assessment of English language learner's speech, with focus on early speakers. 
- Support for _monologic_ and _dialogic_ oral productions (the dialog is between the learner and the teacher)
- A 9-point scale based reporting that is sensitive to early speakers' abilities in their home language(s)
- Recommendations of audio stories for learners to listen to, to improve listening skills, vocabulary and overall proficiency in the language (Work in progress)

### Hardware and software requirements
To successfully install and run ELA, the following are the minimum requirements.
- A desktop / laptop computer with 8 GB RAM, 4 CPU cores, 50 GB disk space is sufficient. Note: The AI components are resource intensive when they are running. Avoid actively running/using other software when the AI components are executing.
- Any standard Linux OS distribution. While other OSes/versions should work, ELA is developed and tested on Linux, specifically Ubuntu 22.04+
- The desktop should have the following software installed
  - Docker CE
  - [KDE Connect app](https://kdeconnect.kde.org/) to transfer files between ELA Web and ELA Collect. An alternative to this software is raw Bluetooth connectivity, but working with Bluetooth connections directly is harder.
- A USB storage device with about 20 GB space for the ELA software, AI models and tutorial materials, and a working USB port on the desktop computer.
- An android mobile phone with Android OS version 10 or above (ensure the phone microphone is in working condition)

### What is the AI in ELA?
ELA uses the following AI and Machine Learning components
- [pyannote](https://github.com/pyannote/pyannote-audio), for speaker diarization to separate learner and teacher speech in conversations
- [whisper](https://github.com/openai/whisper), for spoken language identification and transcription of learner speech
- [spaCy](https://spacy.io/), for natural language processing of transcribed learner speech
- A custom grammar model built on the lines of [vennify](https://huggingface.co/vennify/t5-base-grammar-correction), supported by the [Errant](https://github.com/chrisjbryant/errant) library
