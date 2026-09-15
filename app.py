import streamlit as st
from PIL import Image, ImageDraw
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

st.set_page_config(page_title="Honeybee Colony Assessment", page_icon="🐝", layout="wide")
st.markdown("<h1 style='color:#083256'>🐝 Honeybee Colony Assessment System</h1>", unsafe_allow_html=True)
st.caption("AI-based image tagging, quantification and temporal colony monitoring")
st.divider()

mode=st.sidebar.radio("Module",["Image Analysis","Temporal Analysis","Dataset / Annotation"])
st.sidebar.info("Prototype mode: illustrative inference. Connect the trained honeybee-specific YOLO/segmentation model after dataset development.")

def annotate(img):
    img=img.convert("RGB").copy(); d=ImageDraw.Draw(img); w,h=img.size
    boxes=[("Bee",.10,.12,.20,.21),("Bee",.28,.27,.39,.37),("Pollen Bee",.48,.10,.61,.22),
           ("Bee",.68,.33,.79,.44),("Dead Bee",.76,.60,.86,.70),
           ("Brood",.05,.64,.31,.91),("Honey",.69,.65,.94,.90),("Pollen",.34,.52,.57,.72)]
    for lab,x1,y1,x2,y2 in boxes:
        a,b,c,e=int(x1*w),int(y1*h),int(x2*w),int(y2*h)
        d.rectangle((a,b,c,e),outline=(244,92,22),width=max(3,w//300))
        tw=max(100,len(lab)*10); d.rectangle((a,b,a+tw,b+30),fill=(8,50,86)); d.text((a+6,b+6),lab,fill="white")
    return img

if mode=="Image Analysis":
    st.subheader("Upload Hive Image")
    f=st.file_uploader("Upload a honeybee hive/frame photograph",type=["jpg","jpeg","png"])
    use=st.checkbox("Use included sample image",True)
    img=Image.open(f) if f else (Image.open(Path(__file__).parent/"sample_hive_frame.png") if use else None)
    if img:
        c1,c2=st.columns(2)
        with c1: st.markdown("### Original Image"); st.image(img,use_container_width=True)
        with c2:
            st.markdown("### AI Detection / Tagging")
            st.image(annotate(img),use_container_width=True)
        st.success("Prototype analysis complete.")
        vals=[("Visible bees",127),("Pollen-carrying bees",18),("Dead bees",3),("Suspected mites",1),("Brood area","42%"),("Honey area","21%"),("Pollen area","8%")]
        st.markdown("### Colony Assessment")
        for cols,chunk in [(st.columns(4),vals[:4]),(st.columns(3),vals[4:])]:
            for col,(k,v) in zip(cols,chunk): col.metric(k,v)
        st.warning("These values are illustrative demo outputs, not trained-model predictions.")
        st.dataframe(pd.DataFrame({"Class":["Bee","Pollen Bee","Dead Bee","Suspected Mite","Brood","Honey","Pollen"],
                                   "Count / Coverage":[127,18,3,1,"42%","21%","8%"]}),use_container_width=True,hide_index=True)

elif mode=="Temporal Analysis":
    st.subheader("Temporal Colony Analysis")
    st.caption("Illustrative time-series for demonstrating the planned module.")
    dates=pd.to_datetime(["2026-09-01","2026-09-05","2026-09-10","2026-09-15"])
    bees=[85,97,112,127]; brood=[32,37,39,42]; pollen=[5,6,7,8]
    c1,c2=st.columns(2)
    with c1:
        fig,ax=plt.subplots(); ax.plot(dates,bees,marker="o"); ax.set(title="Visible Bee Count",ylabel="Count",xlabel="Date"); fig.autofmt_xdate(); st.pyplot(fig); plt.close(fig)
    with c2:
        fig,ax=plt.subplots(); ax.plot(dates,brood,marker="o",label="Brood %"); ax.plot(dates,pollen,marker="o",label="Pollen %"); ax.set(title="Frame Area Indicators",ylabel="Percentage",xlabel="Date"); ax.legend(); fig.autofmt_xdate(); st.pyplot(fig); plt.close(fig)
    st.dataframe(pd.DataFrame({"Date":dates.strftime("%d %b %Y"),"Visible Bees":bees,"Brood Area (%)":brood,"Pollen Area (%)":pollen}),use_container_width=True,hide_index=True)

else:
    st.subheader("Dataset & Annotation Workflow")
    st.markdown("""
**Image Acquisition → CVAT Annotation → Dataset Validation → Train/Validation/Test Split → Model Training**

**Initial classes:** Bee • Dead bee • Pollen-carrying bee • Brood area • Honey • Pollen • Suspected Varroa mite (where visible)

**Metadata:** Date/time • Hive/frame location • Image source • Annotation information • Expert verification
""")
    st.info("CVAT creates the labelled computer-vision dataset; it is not the AI prediction model.")

st.divider()
st.caption("Panel-demo prototype • AI outputs require expert verification • Initial scope: one honeybee box")
