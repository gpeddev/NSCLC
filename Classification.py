#       Load pooling
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from Pooling.Pooling import pooling
from SupportCode.Paths import CropTumor, CroppedWindow
from sklearn.metrics import f1_score
import pandas as pd
import numpy as np
from group_lasso import LogisticGroupLasso
np.random.seed(0)
LogisticGroupLasso.LOG_LOSSES = True


vae_1_latent_space=256
vae_2_latent_space=256
# Load clinical data
data = pd.read_csv("ClinicalDataAnalysis/data.csv")
data.reset_index()
# create new column names
column_names_vae1=[]
for i in range(vae_1_latent_space*2):
    column_names_vae1.append("VAE1-"+str(i))
column_names_vae2=[]
for i in range(vae_2_latent_space*2):
    column_names_vae2.append("VAE2-"+str(i))
# load vectors from 5 kfold models
print("Pooling VAE 1")
pool_rslt_1=pooling("./BestResults/VAE_1/Model_1/19_2022-08-10_01_53_19/Models", vae_1_latent_space, CropTumor)
print("Pooling VAE 2")
pool_rslt_2=pooling("./BestResults/VAE_2/Model_1/17_2022-08-15_19_47_42/Models", vae_2_latent_space, CroppedWindow)

# create pandas from dictionary
kfold_list_features1=[]
kfold_list_features2=[]
for i in range(5):
    temp1 = pd.DataFrame.from_dict(pool_rslt_1[i], orient='index', columns=column_names_vae1)
    temp1 = temp1.reset_index()
    temp1.rename(columns={"index": "Case ID"}, inplace=True)
    temp2 = pd.DataFrame.from_dict(pool_rslt_2[i], orient='index', columns=column_names_vae2)
    temp2 = temp2.reset_index()
    temp2.rename(columns={"index": "Case ID"}, inplace=True)
    kfold_list_features1.append(temp1)
    kfold_list_features2.append(temp2)





################################ work with one to begin with
new_data=pd.merge(data, kfold_list_features1[0])
new_data=pd.merge(new_data,kfold_list_features2[0])

##################################################################### LASSO

new_data["%GG"].unique()
new_data["%GG"]=new_data["%GG"].replace('0%',0)
new_data["%GG"]=new_data["%GG"].replace('>0 - 25%',1)
new_data["%GG"]=new_data["%GG"].replace('50 - 75%',2)
new_data["%GG"]=new_data["%GG"].replace('25 - 50%',3)
new_data["%GG"]=new_data["%GG"].replace('75 - < 100%',4)
new_data["%GG"]=new_data["%GG"].replace('100%',5)
new_data["%GG"].unique()

new_data["Recurrence"]=new_data["Recurrence"].replace("yes",1)
new_data["Recurrence"]=new_data["Recurrence"].replace("no",0)


new_data.drop("Case ID",inplace=True,axis=1)
dummies=["Gender","Ethnicity", "Smoking status", "Tumor Location (choice=RUL)", "Tumor Location (choice=RML)",
         "Tumor Location (choice=RLL)","Tumor Location (choice=LUL)","Tumor Location (choice=LLL)",
         "Tumor Location (choice=L Lingula)","Histology","Pathological T stage","Pathological N stage",
         "Pathological M stage","Histopathological Grade","Pleural invasion (elastic, visceral, or parietal)",
         "Adjuvant Treatment","Chemotherapy","Radiation"]
new_data["Pathological T stage"].unique()
new_data["Histopathological Grade"].unique()

counter=1
pre=[]
y=new_data["Recurrence"]
x=new_data.drop("Recurrence",axis=1)
# Normalization
numerics=x.select_dtypes(include=np.number).columns.tolist()
x[numerics]=(x[numerics]-x[numerics].min())/(x[numerics].max()-x[numerics].min())

for col_name in dummies:
    number_of_unique_values=x[col_name].unique().size
    pre=pre+[counter]*number_of_unique_values
    counter=counter+1
x.columns.size

dc=pd.get_dummies(x,columns=dummies)
dc.columns.size

prepre=[]
for i in range(dc.columns.size-len(pre)):
    prepre=prepre+[counter]
    counter=counter+1
#groups=[None]*(dc.columns.size-len(pre))+pre

groups=prepre+pre


pipe = Pipeline(
    memory=None,
    steps=[
        ("variable_selection",
         LogisticGroupLasso(
             groups=groups,
             group_reg=0.00001,
#             group_reg=0.00001,    F1 score: 0.9736842105263158 accuracy: 0.9859154929577465
             l1_reg=0,
             tol=1e-5,
             #subsampling_scheme=1,
             supress_warning=True,
             n_iter=100000 )
         ),
#        ("regressor", LogisticRegression())
        ("regressor", SVC())
         ])



pipe.fit(dc, y)

# Extract from pipeline
yhat = pipe.predict(dc)
sparsity_mask = pipe["variable_selection"].sparsity_mask_

acc= (yhat == y).mean()
f1score = f1_score(y, yhat, average="binary")
# Print performance metrics
print(f"Number variables: {len(sparsity_mask)}")
print(f"Number of chosen variables: {sparsity_mask.sum()}")
print(f"F1 score: {f1score} accuracy: {acc}")
group_lasso_results= dc.loc[:, sparsity_mask]
X=group_lasso_results

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.20)

svclassifier = SVC(kernel='linear')
svclassifier.fit(X_train, y_train)
y_pred = svclassifier.predict(X_test)
print(confusion_matrix(y_test, y_pred))
print(classification_report(y_test, y_pred))
scores = cross_val_score(svclassifier, X, y, cv=5)
scores
print("%0.2f accuracy with a standard deviation of %0.2f" % (scores.mean(), scores.std()))

svclassifier = SVC(kernel='poly')
svclassifier.fit(X_train, y_train)
y_pred = svclassifier.predict(X_test)
print(confusion_matrix(y_test, y_pred))
print(classification_report(y_test, y_pred))
scores = cross_val_score(svclassifier, X, y, cv=5)
scores
print("%0.2f accuracy with a standard deviation of %0.2f" % (scores.mean(), scores.std()))

svclassifier = SVC(kernel='rbf',degree=5)
svclassifier.fit(X_train, y_train)
y_pred = svclassifier.predict(X_test)
print(confusion_matrix(y_test, y_pred))
print(classification_report(y_test, y_pred))
scores = cross_val_score(svclassifier, X, y, cv=5)
scores
print("%0.2f accuracy with a standard deviation of %0.2f" % (scores.mean(), scores.std()))


svclassifier = SVC(kernel='sigmoid')
svclassifier.fit(X_train, y_train)
y_pred = svclassifier.predict(X_test)
print(confusion_matrix(y_test, y_pred))
print(classification_report(y_test, y_pred))
scores = cross_val_score(svclassifier, X, y, cv=5)
scores
print("%0.2f accuracy with a standard deviation of %0.2f" % (scores.mean(), scores.std()))