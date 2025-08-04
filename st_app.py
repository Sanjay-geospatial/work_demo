import geopandas as gpd
import streamlit as st
from fpdf import FPDF
from io import BytesIO
import ee
import geemap
import pandas as pd

st.set_page_config(
    page_title="Deforestation analyser",
    layout="wide",
    initial_sidebar_state="expanded")

st.write('Deforestation analysis for coffee farms')

col1, col2 = st.columns(2)

cluster = st.sidebar.selectbox('Select cluster', ['Hassan', 'Kodagu', 'Chikkamagalur'])
if cluster:
    st.write(cluster)

farm_id = st.sidebar.text_input("Enter farm ID")

if farm_id:
 
    st.write(f"Cluster: {cluster}")
    st.write(f"Farm ID: {farm_id}")

    try:
        print('reading the farm boundary..')
        gdf = gpd.read_file('https://raw.githubusercontent.com/Sanjay-geospatial/work_demo/refs/heads/main/mysore.geojson')
        print('read complete')
        if gdf.empty:
            st.warning("No data found for the given cluster and farm ID.")
        else:

            try:
                ee.Initialize('ee-sanjaymanjappa25')
            except:
                ee.Authenticate()
                ee.Initialize('ee-sanjaymanjappa25')

            roi = geemap.gdf_to_ee(gdf)

            style = {
                "color": "red",  
                "fillColor": "00000000",
                "width": 2              
            }

            Map = geemap.Map()
            Map.centerObject(roi, zoom=17)
            Map.addLayer(roi.style(**style), {}, "Farm Boundary")
            Map.to_image("farm_boundary_map.png", width=800, height=600)

            with col1:
                st.header('Farm boundary')
                st.image("farm_boundary_map.png")

            data = ee.Image("UMD/hansen/global_forest_change_2024_v1_12")

            loss_year = data.select('lossyear')

            loss = data.select("loss")

            loss_mask = loss_year.gte(20).And(loss_year.lte(23))

            loss_filtered = data.select('loss').updateMask(loss_mask)

            with col2:
                st.header('Deforestation')
                Map.addLayer(loss_filtered, {'min': 0, 'max': 1, 'palette': ['red', 'green', 'orange', 'yellow']}, 'Loss 2020–2023')
                Map.to_image("Deforestation_map.png", width=800, height=600)

            years = list(range(2020, 2024))

            def get_yearly_loss(year):
                year_image = loss_year.eq(year - 2000).And(loss)
                pixel_area = ee.Image.pixelArea().multiply(0.000247) 
                area_image = year_image.multiply(pixel_area)
                stats = area_image.reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi,
                    scale=30,
                    maxPixels=1e13
                )
                return ee.Number(stats.get('lossyear')).getInfo() or 0

            area_by_year = {str(y): get_yearly_loss(y) for y in years}
            deforestation_df = pd.DataFrame(list(area_by_year.items()), columns=["year", "deforested_area"])
                        
            st.subheader('Deforestation loss by year')
            deforestation_trend = deforestation_df.plot(kind = 'bar', x = 'year', y = 'deforested_area')

            if st.button('Generate report'):
                class PDF(FPDF):
                    def header(self):
                        self.image('ecom.png', 10, 8, 25)
                        self.set_font('helvetica', 'B', 20)
                        self.cell(40, 10, f'Deforestation report of', 
                         ln = True, align = 'C')
                        self.ln(20)

                    def footer(self):
                        self.set_y(-15)
                        self.set_font('helvetica', 'I', 10)
                        self.cell(0, 10, f'page no. {self.page_no()}', align = 'C', ln=True)
                        self.set_font('helvetica', 'I', 10)
                        self.text_color(169, 169, 169)
                        self.cell(0, 10, 'Ecom India pvt. ltd.')


                pdf = PDF('P', 'mm', 'Letter')
                pdf.set_auto_page_break(True, 15)
                pdf.add_page()

                pdf.image("farm_boundary_map.png", x=30, y=50, w=150)

                pdf.add_page()
                pdf.set_font('helvetica', 'BIU', 16)
                pdf.set_text_color(220, 50, 50)
                pdf.cell(40, 10, 'Deforestation map', 
                         ln = True, border = True)
                pdf.image("Deforestation_map.png", x=15, y=40, w=85)

                pdf.cell(40, 10, 'Deforestation history', 
                         ln = True, border = True)
                pdf.image(deforestation_trend, x=110, y=40, w=85)
                deforestation_report = pdf.output(f'Deforestation report ')

            
                pdf_buffer = BytesIO()
                pdf.output(pdf_buffer)
                pdf_buffer.seek(0)

            if deforestation_report:
                st.download_button(
                    label="Download report",
                    data= pdf_buffer,
                    icon=":material/download:",
                )


    
    except Exception as e:    
        st.error(f"Error loading data: {e}")



