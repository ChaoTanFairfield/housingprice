import streamlit as st
import pandas as pd
import pydeck as pdk
from geopy.geocoders import Nominatim
from concurrent.futures import ThreadPoolExecutor
import requests

st.set_page_config(page_title="FairVision - Property Search", layout="wide")

geolocator = Nominatim(user_agent="fairvision_app")

@st.cache_data(ttl=24*3600) 
def geocode_address(address):
    try:
        location = geolocator.geocode(address.split(',')[0], timeout=5)
        if location:
            return (location.latitude, location.longitude)
    except:
        pass
    return (None, None)

def batch_geocode(addresses):
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(geocode_address, addresses))
    return results

@st.cache_data
def load_data():
    data = pd.read_csv("newdata.csv")
    
    def get_latest_price(row):
        for i in range(1, 6):
            price_col = f"Sale_Price_{i}"
            if pd.notna(row[price_col]):
                return row[price_col]
        return 0
    
    data['Latest_Price'] = data.apply(get_latest_price, axis=1)
    data['Total Bedrooms'] = data['Total Bedrooms'].fillna(0).astype(int)
    data['Total Full Baths'] = data['Total Full Baths'].fillna(0).astype(int)
    data['Total Half Baths'] = data['Total Half Baths'].fillna(0).astype(int)
    data['Assessed Value'] = data['Assessed Value'].fillna(0).astype(int)
    data['Year Built:'] = data['Year Built:'].fillna(0).astype(int)
    data['Fireplaces'] = data['Fireplaces'].fillna(0).astype(int)
    
    data['Price'] = data['Latest_Price'].apply(
        lambda x: f"${x/1000:.1f}k" if x >= 1000 else f"${x:.0f}"
    )
    
    data['Baths'] = data.apply(
        lambda row: f"{row['Total Full Baths']} Full, {row['Total Half Baths']} Half", 
        axis=1
    )
    
    data['Heat Type'] = data['Heat Type:'].fillna('Unknown')
    data['Heat Fuel'] = data['Heat Fuel:'].fillna('Unknown')
    data['Central AC'] = data['AC Type:'].apply(lambda x: 'Yes' if x == 'Central' else 'No')
    
    return data

def property_card(property_data):
    with st.container():
        col1, col2 = st.columns([1, 2])
        with col2:
            st.markdown(f"### {property_data['Address'].split(',')[0]}")
            st.markdown(f"**{property_data['Address'].split(',')[1].strip()}**")
        
            
            cols1 = st.columns(4)
            cols1[0].markdown(f"**Beds:** {property_data['Total Bedrooms']}")
            cols1[1].markdown(f"**Baths:** {property_data['Baths']}")
            cols1[2].markdown(f"**Sqft:** {property_data.get('Living Area:', 'N/A')}")
            cols1[3].markdown(f"**Type:** {property_data['Style:']}")
            
            cols2 = st.columns(4)
            cols2[0].markdown(f"**Year Built:** {property_data.get('Year Built:', 'N/A')}")
            cols2[1].markdown(f"**Stories:** {property_data.get('Stories:', 'N/A')}")
            cols2[2].markdown(f"**Rooms:** {property_data.get('Total Rooms', 'N/A')}")
            cols2[3].markdown(f"**Fireplaces:** {property_data.get('Fireplaces', 0)}")
            
            cols3 = st.columns(4)
            cols3[0].markdown(f"**Heat Type:** {property_data.get('Heat Type', 'N/A')}")
            cols3[1].markdown(f"**Heat Fuel:** {property_data.get('Heat Fuel', 'N/A')}")
            cols3[2].markdown(f"**AC Type:** {property_data.get('AC Type:', 'N/A')}")
            cols3[3].markdown(f"**Assessed Value:** ${property_data.get('Assessed Value', 'N/A'):,}")
            
            with st.expander("Owner History"):
                owners = []
                for i in range(1, 6):
                    owner_col = f"Owner_{i}"
                    price_col = f"Sale_Price_{i}"
                    date_col = f"Sale_Date_{i}"
                    
                    if pd.notna(property_data.get(owner_col)):
                        owner_info = {
                            "owner": property_data[owner_col],
                            "price": f"${property_data[price_col]:,}" if pd.notna(property_data.get(price_col)) else "N/A",
                            "date": property_data[date_col].split()[0] if pd.notna(property_data.get(date_col)) else "N/A"
                        }
                        owners.append(owner_info)
                
                if owners:
                    for owner in owners:
                        st.markdown(f"**{owner['owner']}** - {owner['price']} on {owner['date']}")
                else:
                    st.markdown("No owner history available")
            
            btn_cols = st.columns(3)
            btn_cols[0].button("View Details", key=f"details_{property_data.name}")
            btn_cols[1].button("Save", key=f"save_{property_data.name}")
            btn_cols[2].button("Contact", key=f"contact_{property_data.name}")
        st.divider()

def main():
    st.markdown("""
    <style>
        .stApp { background-color: #f5f5f5; }
        .property-card {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .stButton>button { width: 100%; border-radius: 4px; }
        .map-container {
            margin-bottom: 20px;
        }
        .st-expander .stMarkdown { font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

    housing_data = load_data()

    st.sidebar.header("🔍 Filters")
    with st.sidebar:
        st.subheader("Property Details")
        bedrooms = st.selectbox(
            "Minimum bedrooms",
            options=["Any", "1+", "2+", "3+", "4+", "5+"],
            index=0
        )

        bathrooms = st.selectbox(
            "Minimum full bathrooms",
            options=["Any", "1+", "2+", "3+"],
            index=0
        )

        min_sqft = st.number_input(
            "Minimum sqft", 
            min_value=0, 
            value=0,
            step=10
        )
        
        property_types = st.multiselect(
            "Property Type",
            options=housing_data['Style:'].unique(),
            default=None
        )

        st.subheader("Location & Price")
        pincode = st.text_input("ZIP code")

        min_price, max_price = int(housing_data['Latest_Price'].min()/1000), int(housing_data['Latest_Price'].max()/1000)
        price_range = st.slider(
            "Last Sale Price Range ($k)", 
            min_value=min_price, 
            max_value=max_price, 
            value=(min_price, max_price),
            step=10
        )
        
        st.subheader("HVAC Features")
        central_ac = st.selectbox(
            "Central AC",
            options=["Any", "Yes", "No"],
            index=0
        )
        
        heat_types = st.multiselect(
            "Heat Type",
            options=housing_data['Heat Type'].unique(),
            default=None
        )
        
        heat_fuels = st.multiselect(
            "Heat Fuel",
            options=housing_data['Heat Fuel'].unique(),
            default=None
        )
        
        st.subheader("Additional Features")
        has_fireplace = st.checkbox("Fireplace")
    
        apply_filters = st.button("Apply Filters")

    if apply_filters or st.session_state.get('show_results', False):
        st.session_state.show_results = True
        
        filtered = housing_data.copy()
        
        if property_types:
            filtered = filtered[filtered['Style:'].isin(property_types)]
        
        if bedrooms != "Any":
            min_beds = int(bedrooms[0])
            filtered = filtered[filtered['Total Bedrooms'] >= min_beds]
        
        if bathrooms != "Any":
            min_baths = int(bathrooms[0])
            filtered = filtered[filtered['Total Full Baths'] >= min_baths]
        
        if pincode:
            filtered = filtered[filtered['Pincode'].astype(str).str.startswith(pincode)]
        
        if has_fireplace:
            filtered = filtered[filtered['Fireplaces'] > 0]
        
        if min_sqft > 0:
            filtered = filtered[filtered['Living Area:'] >= min_sqft]
        
        if central_ac != "Any":
            filtered = filtered[filtered['Central AC'] == central_ac]
        
        if heat_types:
            filtered = filtered[filtered['Heat Type'].isin(heat_types)]
        
        if heat_fuels:
            filtered = filtered[filtered['Heat Fuel'].isin(heat_fuels)]
        
        filtered = filtered[filtered['Latest_Price'].between(
            price_range[0]*1000, 
            price_range[1]*1000
        )]
        
        st.header("Property Locations")
        mapped = filtered.copy()
        
        missing_coords = mapped[(mapped['Latitude'].isna()) | (mapped['Longitude'].isna())]
        if not missing_coords.empty:
            with st.spinner('Mapping properties...'):
                coords = batch_geocode(missing_coords['Address'].tolist())
                mapped.loc[(mapped['Latitude'].isna()) | (mapped['Longitude'].isna()), 'Latitude'] = [c[0] for c in coords]
                mapped.loc[(mapped['Latitude'].isna()) | (mapped['Longitude'].isna()), 'Longitude'] = [c[1] for c in coords]
        
        mapped = mapped.dropna(subset=['Latitude', 'Longitude'])
        
        if not mapped.empty:
            ICON_URL = "https://maps.google.com/mapfiles/ms/icons/red-dot.png"
            
            icon_data = {
                "url": ICON_URL,
                "width": 32,
                "height": 32,
                "anchorY": 32
            }
            
            mapped["icon_data"] = None
            for i in mapped.index:
                mapped["icon_data"][i] = icon_data
            
            icon_layer = pdk.Layer(
                "IconLayer",
                data=mapped,
                get_icon="icon_data",
                get_position='[Longitude, Latitude]',
                get_size=4,
                size_scale=10,
                pickable=True
            )
            
            scatter_layer = pdk.Layer(
                'ScatterplotLayer',
                data=mapped,
                get_position='[Longitude, Latitude]',
                get_color='[255, 0, 0, 160]',
                get_radius=50,
                pickable=True,
                radius_min_pixels=3,
                radius_max_pixels=6
            )
            
            tooltip = {
                "html": """
                <div style="padding: 5px;">
                    <b>Address:</b> {Address}<br/>
                    <b>Price:</b> {Price}<br/>
                    <b>Bedrooms:</b> {Total Bedrooms}<br/>
                    <b>Baths:</b> {Baths}
                </div>
                """,
                "style": {
                    "backgroundColor": "white",
                    "color": "black",
                    "fontFamily": '"Helvetica Neue", Arial',
                    "zIndex": "10000",
                    "borderRadius": "4px",
                    "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
                }
            }
            
            view_state = pdk.ViewState(
                latitude=mapped['Latitude'].mean(),
                longitude=mapped['Longitude'].mean(),
                zoom=11,
                pitch=0
            )
            
            layers = [scatter_layer, icon_layer]
            
            with st.container():
                st.pydeck_chart(pdk.Deck(
                    map_style='mapbox://styles/mapbox/light-v9',
                    initial_view_state=view_state,
                    layers=layers,
                    tooltip=tooltip
                ))
        else:
            st.warning("No properties with valid location data")
        
        st.header("Available Properties")
        
        if not filtered.empty:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{len(filtered)} properties found**")
            with col2:
                sort_option = st.selectbox(
                    "Sort by", 
                    ["Price: Low to High", "Price: High to Low", "Bedrooms", "Bathrooms", "Year Built"]
                )
            
            if sort_option == "Price: Low to High":
                filtered = filtered.sort_values(by='Latest_Price')
            elif sort_option == "Price: High to Low":
                filtered = filtered.sort_values(by='Latest_Price', ascending=False)
            elif sort_option == "Bedrooms":
                filtered = filtered.sort_values(by='Total Bedrooms', ascending=False)
            elif sort_option == "Bathrooms":
                filtered = filtered.sort_values(by='Total Full Baths', ascending=False)
            elif sort_option == "Year Built":
                filtered = filtered.sort_values(by='Year Built:', ascending=False)
            
            for idx, row in filtered.iterrows():
                property_card(row)
        else:
            st.warning("No properties match your criteria")
    else:
        st.info("Please apply filters to see properties")

if __name__ == "__main__":
    main()
