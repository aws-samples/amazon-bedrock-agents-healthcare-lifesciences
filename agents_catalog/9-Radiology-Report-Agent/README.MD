## Create an agent for Validating Radiology Report 
A solution has been developed using Amazon Nova and Bedrock to revolutionize radiology reporting workflows. This system automates two critical tasks: validating reports against ACR guidelines and generating accurate impression summaries from findings. Using Retrieval Augmented Generation with a knowledge base of 90,000+ radiology reports, the solution ensures high-quality, compliant reporting. The system's effectiveness is validated through a comprehensive LLM-as-a-judge evaluation framework using Claude 3 Haiku, demonstrating consistent performance across multiple quality metrics. This automation can save radiologists 1-2 hours daily while being 75% more cost-effective than comparable solutions, ultimately improving healthcare delivery and reducing burnout.

Please run the python notebook `create_agent.ipynb` for 

## Test Case1: Chest Radiology Report
Here is the radiology report: FINAL REPORT EXAMINATION : CHEST ( PORTABLE AP ) INDICATION : History :___ F with ett placement TECHNIQUE : Upright AP view of the chest COMPARISON : None . Patient is currently listed as EU critical . 
FINDINGS : Endotracheal tube tip terminates approximately a 4.6 cm from the carina . Enteric tube tip terminates within the distal esophagus and should be advanced by at least 11 cm .Heart size is normal . Gaseous distension of the stomach is noted "

### Output
In this case the agent downloads the ACR guidance criteria from an S3 bucket. It then validates the report against the same criteria

## Test Case 2: Transthoracic Ultrasound Report
Transthoracic echocardiogram was performed of technically limited quality. The left ventricle was normal in size and dimensions with normal LV function. Ejection fraction was 50% to 55%. Concentric hypertrophy noted with interventricular septum measuring 1.6 cm, posterior wall measuring 1.2 cm. Left atrium is enlarged, measuring 4.42 cm. Right-sided chambers are normal in size and dimensions. Aortic root has normal diameter. Mitral and tricuspid valve reveals annular calcification. Fibrocalcific valve leaflets noted with adequate excursion. Similar findings noted on the aortic valve as well with significantly adequate excursion of valve leaflets. Atrial and ventricular septum are intact.Pericardium is intact without any effusion. No obvious intracardiac mass or thrombi noted. Doppler study reveals mild-to-moderate mitral regurgitation. Severe aortic stenosis with peak velocity of 2.76 with calculated ejection fraction 50% to 55% with severe aortic stenosis. There is also mitral stenosis."

### Output
In this case, the agent cannot find the guidance document, so it provides its own report based on the inherent knowledge in the absence of any specific guidance criteria.
