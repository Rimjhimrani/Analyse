import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime
import io
import base64
from matplotlib.figure import Figure
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Set page config
st.set_page_config(
    page_title="Enhanced Inventory Analysis with Vendor Filter",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .status-excess {
        border-left-color: #007bff !important;
    }
    .status-short {
        border-left-color: #dc3545 !important;
    }
    .status-normal {
        border-left-color: #28a745 !important;
    }
    .status-total {
        border-left-color: #6c757d !important;
    }
    .vendor-filter {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #bee5eb;
        margin: 1rem 0;
    }
    .graph-description {
        background-color: #f8f9fa;
        padding: 0.8rem;
        border-radius: 0.3rem;
        border-left: 3px solid #007bff;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: #495057;
    }
</style>
""", unsafe_allow_html=True)

class InventoryAnalyzer:
    def __init__(self):
        self.status_colors = {
            'Within Norms': '#28a745',      # Green
            'Excess Inventory': '#007bff',   # Blue
            'Short Inventory': '#dc3545'     # Red
        }
        
    def safe_float_convert(self, value):
        """Safely convert string to float, handling commas and other formatting"""
        if pd.isna(value) or value == '' or value is None:
            return 0.0
        
        str_value = str(value).strip()
        str_value = str_value.replace(',', '').replace(' ', '')
        
        if str_value.endswith('%'):
            str_value = str_value[:-1]
        
        try:
            return float(str_value)
        except (ValueError, TypeError):
            return 0.0
    
    def safe_int_convert(self, value):
        """Safely convert string to int, handling commas and other formatting"""
        if pd.isna(value) or value == '' or value is None:
            return 0
        
        str_value = str(value).strip()
        str_value = str_value.replace(',', '').replace(' ', '')
        
        try:
            return int(float(str_value))
        except (ValueError, TypeError):
            return 0
    
    def load_sample_data(self):
        """Load sample inventory data with vendor information"""
        inventory_sample = [
            ["AC0303020106", "FLAT ALUMINIUM PROFILE", "5.230", "4.000", "496", "Vendor_A"],
            ["AC0303020105", "RAIN GUTTER PROFILE", "8.360", "6.000", "1984", "Vendor_B"],
            ["AA0106010001", "HYDRAULIC POWER STEERING OIL", "12.500", "10.000", "2356", "Vendor_A"],
            ["AC0203020077", "Bulb beading LV battery flap", "3.500", "3.000", "248", "Vendor_C"],
            ["AC0303020104", "L- PROFILE JAM PILLAR", "15.940", "20.000", "992", "Vendor_A"],
            ["AA0112014000", "Conduit Pipe Filter to Compressor", "25", "30", "1248", "Vendor_B"],
            ["AA0115120001", "HVPDU ms", "18", "12", "1888", "Vendor_D"],
            ["AA0119020017", "REAR TURN INDICATOR", "35", "40", "1512", "Vendor_C"],
            ["AA0119020019", "REVERSING LAMP", "28", "20", "1152", "Vendor_A"],
            ["AA0822010800", "SIDE DISPLAY BOARD", "42", "50", "2496", "Vendor_B"],
            ["BB0101010001", "ENGINE OIL FILTER", "65", "45", "1300", "Vendor_E"],
            ["BB0202020002", "BRAKE PAD SET", "22", "25", "880", "Vendor_C"],
            ["CC0303030003", "CLUTCH DISC", "8", "12", "640", "Vendor_D"],
            ["DD0404040004", "SPARK PLUG", "45", "35", "450", "Vendor_A"],
            ["EE0505050005", "AIR FILTER", "30", "28", "600", "Vendor_B"],
            ["FF0606060006", "FUEL FILTER", "55", "50", "1100", "Vendor_E"],
            ["GG0707070007", "TRANSMISSION OIL", "40", "35", "800", "Vendor_C"],
            ["HH0808080008", "COOLANT", "22", "30", "660", "Vendor_D"],
            ["II0909090009", "BRAKE FLUID", "15", "12", "300", "Vendor_A"],
            ["JJ1010101010", "WINDSHIELD WASHER", "33", "25", "495", "Vendor_B"]
        ]
        
        inventory_data = []
        for row in inventory_sample:
            inventory_data.append({
                'Material': row[0],
                'Description': row[1],
                'QTY': self.safe_float_convert(row[2]),
                'RM IN QTY': self.safe_float_convert(row[3]),
                'Stock_Value': self.safe_int_convert(row[4]),
                'Vendor': row[5]
            })
        
        return inventory_data
    
    def standardize_inventory_data(self, df):
        """Standardize inventory data and extract QTY, RM, and Vendor columns"""
        if df is None or df.empty:
            return []
        
        # Find required columns (case insensitive)
        qty_columns = ['qty', 'quantity', 'current_qty', 'stock_qty']
        rm_columns = ['rm', 'rm_qty', 'required_qty', 'norm_qty', 'target_qty', 'rm_in_qty', 'ri_in_qty']
        material_columns = ['material', 'material_code', 'part_number', 'item_code', 'code', 'part_no']
        desc_columns = ['description', 'item_description', 'part_description', 'desc','part description', 'material_description', 'part_desc']
        value_columns = ['stock_value', 'value', 'amount', 'cost']
        vendor_columns = ['vendor', 'vendor_name', 'supplier', 'supplier_name']
        
        # Get column names (case insensitive)
        available_columns = {k.lower().replace(' ', '_'): k for k in df.columns}
        
        # Find the best matching columns
        qty_col = None
        rm_col = None
        material_col = None
        desc_col = None
        value_col = None
        vendor_col = None
        
        for col_name in qty_columns:
            if col_name in available_columns:
                qty_col = available_columns[col_name]
                break
        
        for col_name in rm_columns:
            if col_name in available_columns:
                rm_col = available_columns[col_name]
                break
        
        for col_name in material_columns:
            if col_name in available_columns:
                material_col = available_columns[col_name]
                break
        
        for col_name in desc_columns:
            if col_name in available_columns:
                desc_col = available_columns[col_name]
                break
        
        for col_name in value_columns:
            if col_name in available_columns:
                value_col = available_columns[col_name]
                break
        
        for col_name in vendor_columns:
            if col_name in available_columns:
                vendor_col = available_columns[col_name]
                break
        
        if not qty_col:
            st.error("QTY/Quantity column not found in inventory file")
            return []
        
        if not rm_col:
            st.error("RM/RM IN QTY column not found in inventory file")
            return []
        
        if not material_col:
            st.error("Material/Part Number column not found in inventory file")
            return []
        
        # Process each record
        standardized_data = []
        for _, record in df.iterrows():
            try:
                material = str(record.get(material_col, '')).strip()
                qty = self.safe_float_convert(record.get(qty_col, 0))
                rm = self.safe_float_convert(record.get(rm_col, 0))
                vendor = str(record.get(vendor_col, 'Unknown')).strip() if vendor_col else 'Unknown'
                
                if material and material.lower() != 'nan' and qty >= 0 and rm >= 0:
                    item = {
                        'Material': material,
                        'Description': str(record.get(desc_col, '')).strip() if desc_col else '',
                        'QTY': qty,
                        'RM IN QTY': rm,
                        'Stock_Value': self.safe_int_convert(record.get(value_col, 0)) if value_col else 0,
                        'Vendor': vendor
                    }
                    standardized_data.append(item)
                    
            except Exception as e:
                continue
        
        return standardized_data
    
    def calculate_variance(self, qty, rm):
        """Calculate variance percentage and absolute value"""
        if rm == 0:
            return 0, 0
        
        variance_percent = ((qty - rm) / rm) * 100
        variance_value = qty - rm
        return variance_percent, variance_value
    
    def determine_status(self, variance_percent, tolerance):
        """Determine inventory status based on variance and tolerance"""
        if abs(variance_percent) <= tolerance:
            return 'Within Norms'
        elif variance_percent > tolerance:
            return 'Excess Inventory'
        else:
            return 'Short Inventory'
    
    def process_data(self, inventory_data, tolerance):
        """Process inventory data and calculate analysis"""
        processed_data = []
        summary_data = {
            'Within Norms': {'count': 0, 'value': 0},
            'Excess Inventory': {'count': 0, 'value': 0},
            'Short Inventory': {'count': 0, 'value': 0}
        }
        
        for item in inventory_data:
            qty = item['QTY']
            rm = item['RM IN QTY']
            stock_value = item['Stock_Value']
            vendor = item['Vendor']
            
            # Calculate variance
            variance_percent, variance_value = self.calculate_variance(qty, rm)
            
            # Determine status
            status = self.determine_status(variance_percent, tolerance)
            
            # Store processed data
            processed_item = {
                'Material': item['Material'],
                'Description': item['Description'],
                'QTY': qty,
                'RM IN QTY': rm,
                'Variance_%': variance_percent,
                'Variance_Value': variance_value,
                'Status': status,
                'Stock_Value': stock_value,
                'Vendor': vendor
            }
            processed_data.append(processed_item)
            
            # Update summary
            summary_data[status]['count'] += 1
            summary_data[status]['value'] += stock_value
        
        return processed_data, summary_data
    
    def get_vendor_summary(self, processed_data):
        """Get summary data by vendor"""
        vendor_summary = {}
        
        for item in processed_data:
            vendor = item['Vendor']
            if vendor not in vendor_summary:
                vendor_summary[vendor] = {
                    'total_parts': 0,
                    'total_qty': 0,
                    'total_rm': 0,
                    'total_value': 0,
                    'short_parts': 0,
                    'excess_parts': 0,
                    'normal_parts': 0,
                    'short_value': 0,
                    'excess_value': 0,
                    'normal_value': 0
                }
            
            vendor_summary[vendor]['total_parts'] += 1
            vendor_summary[vendor]['total_qty'] += item['QTY']
            vendor_summary[vendor]['total_rm'] += item['RM IN QTY']
            vendor_summary[vendor]['total_value'] += item['Stock_Value']
            
            if item['Status'] == 'Short Inventory':
                vendor_summary[vendor]['short_parts'] += 1
                vendor_summary[vendor]['short_value'] += item['Stock_Value']
            elif item['Status'] == 'Excess Inventory':
                vendor_summary[vendor]['excess_parts'] += 1
                vendor_summary[vendor]['excess_value'] += item['Stock_Value']
            else:
                vendor_summary[vendor]['normal_parts'] += 1
                vendor_summary[vendor]['normal_value'] += item['Stock_Value']
        
        return vendor_summary

def create_top_parts_chart(processed_data, status, color):
    """Helper function to create top parts charts"""
    filtered_data = [item for item in processed_data if item['Status'] == status]
    
    if not filtered_data:
        st.info(f"No {status.lower()} parts found.")
        return
    
    # Sort by absolute variance value
    if status == 'Short Inventory':
        sorted_data = sorted(filtered_data, key=lambda x: abs(x['Variance_Value']), reverse=True)[:10]
    else:
        sorted_data = sorted(filtered_data, key=lambda x: x['Variance_Value'], reverse=True)[:10]
    
    materials = [item['Material'] for item in sorted_data]
    variances = [item['Variance_Value'] for item in sorted_data]
    
    fig = go.Figure(data=[
        go.Bar(x=materials, y=variances, marker_color=color)
    ])
    
    fig.update_layout(
        title=f"Top 10 {status} Parts by Variance Value",
        xaxis_title="Material Code",
        yaxis_title="Variance Value",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_vendor_wise_top_parts_chart(processed_data, status, color):
    """Helper function to create vendor-wise top parts charts"""
    filtered_data = [item for item in processed_data if item['Status'] == status]
    
    if not filtered_data:
        st.info(f"No {status.lower()} parts found.")
        return
    
    # Group by vendor and get top parts for each vendor
    vendor_data = {}
    for item in filtered_data:
        vendor = item['Vendor']
        if vendor not in vendor_data:
            vendor_data[vendor] = []
        vendor_data[vendor].append(item)
    
    # Sort each vendor's data and get top parts
    vendor_top_parts = {}
    for vendor, items in vendor_data.items():
        if status == 'Short Inventory':
            sorted_items = sorted(items, key=lambda x: abs(x['Variance_Value']), reverse=True)[:3]
        else:
            sorted_items = sorted(items, key=lambda x: x['Variance_Value'], reverse=True)[:3]
        vendor_top_parts[vendor] = sorted_items
    
    # Create data for plotting
    vendors = []
    materials = []
    variances = []
    
    for vendor, items in vendor_top_parts.items():
        for item in items:
            vendors.append(vendor)
            materials.append(f"{item['Material'][:10]}...")  # Truncate for better display
            variances.append(item['Variance_Value'])
    
    if vendors:
        fig = go.Figure(data=[
            go.Bar(x=vendors, y=variances, marker_color=color, text=materials, textposition='auto')
        ])
        
        fig.update_layout(
            title=f"Top 10 Vendor-wise {status} Parts by Variance Value",
            xaxis_title="Vendor",
            yaxis_title="Variance Value",
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)

def main():
    # Initialize analyzer
    analyzer = InventoryAnalyzer()
    
    # Header
    st.title("📊 Inventory Analyser")
    
    st.markdown(
        "<p style='font-size:18px; font-style:italic; margin-top:-10px; text-align:left;'>"
        "Designed and Developed by Agilomatrix</p>",
        unsafe_allow_html=True
    )
    
    # Sidebar for controls
    st.sidebar.header("⚙️ Control Panel")
    
    # Tolerance setting
    tolerance = st.sidebar.selectbox(
        "Tolerance Zone (+/-)",
        options=[10, 20, 30, 40, 50],
        index=2,  # Default to 30%
        format_func=lambda x: f"{x}%"
    )
    
    # File upload
    uploaded_file = st.sidebar.file_uploader(
        "Upload Inventory File",
        type=['csv', 'xlsx', 'xls'],
        help="Upload a CSV or Excel file with QTY, RM IN QTY, and Vendor columns"
    )
    
    # Load data
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            inventory_data = analyzer.standardize_inventory_data(df)
            
            if inventory_data:
                st.sidebar.success(f"✅ Loaded {len(inventory_data)} inventory items")
            else:
                st.sidebar.error("❌ No valid data found in uploaded file")
                inventory_data = analyzer.load_sample_data()
                st.sidebar.info("Using sample data instead")
        
        except Exception as e:
            st.sidebar.error(f"❌ Error loading file: {str(e)}")
            inventory_data = analyzer.load_sample_data()
            st.sidebar.info("Using sample data instead")
    else:
        inventory_data = analyzer.load_sample_data()
        st.sidebar.info("📋 Using sample data for demonstration")
    
    # Process data
    processed_data, summary_data = analyzer.process_data(inventory_data, tolerance)
    
    # Get vendor list for filtering
    vendors = sorted(list(set(item['Vendor'] for item in processed_data)))
    
    # Vendor filter
    st.sidebar.header("🏢 Vendor Filter")
    selected_vendor = st.sidebar.selectbox(
        "Select Vendor (for Short Inventory focus)",
        options=['All Vendors'] + vendors,
        help="Select a specific vendor to focus on their short inventory items"
    )
    
    # Apply vendor filter for short inventory focus
    if selected_vendor != 'All Vendors':
        st.markdown(f'<div class="vendor-filter">🏢 <strong>Vendor Focus:</strong> {selected_vendor} - Showing Short Inventory Analysis</div>', unsafe_allow_html=True)
        
        # Filter data for selected vendor and short inventory
        vendor_short_items = [item for item in processed_data if item['Vendor'] == selected_vendor and item['Status'] == 'Short Inventory']
        
        if vendor_short_items:
            st.info(f"Found {len(vendor_short_items)} short inventory items for {selected_vendor}")
        else:
            st.success(f"No short inventory items found for {selected_vendor}")
    
    # Display status criteria
    st.info(f"""
    **Status Criteria (Tolerance: ±{tolerance}%)**
    - 🟢 **Within Norms**: QTY = RM IN QTY ± {tolerance}%
    - 🔵 **Excess Inventory**: QTY > RM IN QTY + {tolerance}%
    - 🔴 **Short Inventory**: QTY < RM IN QTY - {tolerance}%
    """)
    
    # Summary Dashboard
    st.header("📈 Summary Dashboard")
    
    # Calculate total value
    total_value = sum(data['value'] for data in summary_data.values())
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card status-normal">', unsafe_allow_html=True)
        st.metric(
            label="🟢 Within Norms",
            value=f"{summary_data['Within Norms']['count']} parts",
            delta=f"₹{summary_data['Within Norms']['value']:,}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card status-excess">', unsafe_allow_html=True)
        st.metric(
            label="🔵 Excess Inventory",
            value=f"{summary_data['Excess Inventory']['count']} parts",
            delta=f"₹{summary_data['Excess Inventory']['value']:,}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card status-short">', unsafe_allow_html=True)
        st.metric(
            label="🔴 Short Inventory",
            value=f"{summary_data['Short Inventory']['count']} parts",
            delta=f"₹{summary_data['Short Inventory']['value']:,}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card status-total">', unsafe_allow_html=True)
        st.metric(
            label="📊 Total Value",
            delta=f"{len(processed_data)} parts",
            value=f"₹{total_value:,}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Vendor Summary
    vendor_summary = analyzer.get_vendor_summary(processed_data)
    
    st.header("🏢 Vendor Summary")
    vendor_df = pd.DataFrame([
        {
            'Vendor': vendor,
            'Total Parts': data['total_parts'],
            'Total QTY': round(data['total_qty'], 2),
            'Total RM': round(data['total_rm'], 2),
            'Short Inventory': data['short_parts'],
            'Excess Inventory': data['excess_parts'],
            'Within Norms': data['normal_parts'],
            'Total Value': f"₹{data['total_value']:,}"
        }
        for vendor, data in vendor_summary.items()
    ])
    
    st.dataframe(vendor_df, use_container_width=True, hide_index=True)
    
    # Fixed: Tabs for different views - corrected the number of tabs to match the tab names
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Graphical Analysis", "🎯 3D Visualization", "📋 Detailed Data", "🏢 Vendor Analysis", "📤 Export"])
    
    with tab1:
        st.header("📊 Graphical Analysis")
        
        # Graph selection
        st.subheader("Select Graphs to Display")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            show_pie = st.checkbox("Status Distribution (Pie)", value=True)
            show_comparison = st.checkbox("QTY vs RM Comparison", value=True)
            show_variance_hist = st.checkbox("Variance Distribution", value=False)
            show_vendor_excess = st.checkbox("Top 10 Vendor-wise Excess Inventory Parts", value=True)
        
        with col2:
            show_excess = st.checkbox("Top Excess Parts", value=True)
            show_short = st.checkbox("Top Short Parts", value=True)
            show_scatter = st.checkbox("QTY vs RM Scatter", value=False)
            show_vendor_short = st.checkbox("Top 10 Vendor-wise Short Inventory Parts", value=True)
        
        with col3:
            show_normal = st.checkbox("Top Normal Parts", value=False)
            show_variance_top = st.checkbox("Top Variance Parts", value=True)
            show_vendor_qty = st.checkbox("Top 10 Vendors by QTY", value=True)
            show_vendor_normal = st.checkbox("Top 10 Vendor-wise Within Norms Parts", value=True)
        
        # Create graphs
        if show_pie:
            st.subheader("📊 Status Distribution")
            st.markdown('<div class="graph-description">This pie chart shows the overall distribution of inventory items across different status categories. It helps identify what percentage of your inventory is within acceptable norms, excess, or short. A balanced inventory typically has the majority of items within norms.</div>', unsafe_allow_html=True)
            
            # Prepare data for pie chart
            status_counts = {status: data['count'] for status, data in summary_data.items() if data['count'] > 0}
            
            if status_counts:
                fig_pie = px.pie(
                    values=list(status_counts.values()),
                    names=list(status_counts.keys()),
                    color=list(status_counts.keys()),
                    color_discrete_map=analyzer.status_colors,
                    title="Inventory Status Distribution"
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
        
        if show_comparison:
            st.subheader("📊 QTY vs RM Comparison")
            st.markdown('<div class="graph-description">This bar chart compares current quantity (QTY) against required minimum quantity (RM IN QTY) for the top 10 highest-value items. It visually shows which items have excess or shortage, helping prioritize inventory adjustments for high-value components.</div>', unsafe_allow_html=True)
            
            # Get top 10 by stock value
            sorted_data = sorted(processed_data, key=lambda x: x['Stock_Value'], reverse=True)[:10]
            
            materials = [item['Material'] for item in sorted_data]
            qty_values = [item['QTY'] for item in sorted_data]
            rm_values = [item['RM IN QTY'] for item in sorted_data]
            
            fig_comparison = go.Figure()
            fig_comparison.add_trace(go.Bar(name='Current QTY', x=materials, y=qty_values, marker_color='#1f77b4'))
            fig_comparison.add_trace(go.Bar(name='RM IN QTY', x=materials, y=rm_values, marker_color='#ff7f0e'))
            
            fig_comparison.update_layout(
                title="QTY vs RM IN QTY Comparison (Top 10 by Stock Value)",
                xaxis_title="Material Code",
                yaxis_title="Quantity",
                barmode='group'
            )
            st.plotly_chart(fig_comparison, use_container_width=True)
        
        if show_vendor_qty:
            st.subheader("🏢 Top 10 Vendors by Current QTY")
            st.markdown('<div class="graph-description">This chart displays the top 10 vendors ranked by their current quantity contribution to your inventory. It helps identify key suppliers and their relative importance in your supply chain, useful for vendor relationship management and risk assessment.</div>', unsafe_allow_html=True)
            
            # Sort vendors by total QTY
            sorted_vendors = sorted(vendor_summary.items(), key=lambda x: x[1]['total_qty'], reverse=True)[:10]
            
            vendor_names = [vendor for vendor, _ in sorted_vendors]
            total_qtys = [data['total_qty'] for _, data in sorted_vendors]
            
            fig_vendor = go.Figure()
            fig_vendor.add_trace(go.Bar(name='Current QTY', x=vendor_names, y=total_qtys, marker_color='#1f77b4'))
            
            fig_vendor.update_layout(
                title="Top 10 Vendors by Total QTY",
                xaxis_title="Vendor",
                yaxis_title="Quantity",
                showlegend=False  # Hide legend since there's only one series
            )
            
            st.plotly_chart(fig_vendor, use_container_width=True)
        
        if show_excess:
            st.subheader("🔵 Top 10 Excess Inventory Parts")
            st.markdown('<div class="graph-description">This chart identifies the top 10 parts with the highest excess inventory by value. These items represent tied-up capital and storage costs. Consider reducing orders for these items or finding alternative uses to optimize cash flow.</div>', unsafe_allow_html=True)
            create_top_parts_chart(processed_data, 'Excess Inventory', analyzer.status_colors['Excess Inventory'])
        
        if show_short:
            st.subheader("🔴 Top 10 Short Inventory Parts")
            st.markdown('<div class="graph-description">This chart shows the top 10 parts with the highest shortage by value. These items pose the greatest risk to operations and require immediate attention. Prioritize restocking these items to avoid production delays or stockouts.</div>', unsafe_allow_html=True)
            create_top_parts_chart(processed_data, 'Short Inventory', analyzer.status_colors['Short Inventory'])
        
        if show_normal:
            st.subheader("🟢 Top 10 Within Norms Parts")
            st.markdown('<div class="graph-description">This chart displays the top 10 parts that are within acceptable inventory norms by stock value. These items represent well-managed inventory with optimal stock levels that balance availability with cost efficiency.</div>', unsafe_allow_html=True)
            create_top_parts_chart(processed_data, 'Within Norms', analyzer.status_colors['Within Norms'])
        
        if show_variance_top:
            st.subheader("📊 Top 10 Parts by Absolute Variance")
            st.markdown('<div class="graph-description">This chart shows the top 10 parts with the highest absolute variance (regardless of excess or shortage). These items have the greatest deviation from target levels and require the most attention in inventory management.</div>', unsafe_allow_html=True)
            
            # Sort by absolute variance value
            sorted_variance = sorted(processed_data, key=lambda x: abs(x['Variance_Value']), reverse=True)[:10]
            
            materials = [item['Material'] for item in sorted_variance]
            variances = [item['Variance_Value'] for item in sorted_variance]
            colors = [analyzer.status_colors[item['Status']] for item in sorted_variance]
            
            fig_variance = go.Figure(data=[
                go.Bar(x=materials, y=variances, marker_color=colors)
            ])
            
            fig_variance.update_layout(
                title="Top 10 Parts by Absolute Variance Value",
                xaxis_title="Material Code",
                yaxis_title="Variance Value",
                showlegend=False
            )
            
            st.plotly_chart(fig_variance, use_container_width=True)
        
        if show_variance_hist:
            st.subheader("📊 Variance Distribution Histogram")
            st.markdown('<div class="graph-description">This histogram shows the distribution of variance percentages across all inventory items. It helps understand the overall pattern of inventory deviations and identify if most items cluster around the target or if there are systematic issues.</div>', unsafe_allow_html=True)
            
            variance_percentages = [item['Variance_%'] for item in processed_data]
            
            fig_hist = px.histogram(
                x=variance_percentages,
                bins=20,
                title="Distribution of Variance Percentages",
                labels={'x': 'Variance Percentage (%)', 'y': 'Number of Items'}
            )
            
            # Add vertical lines for tolerance zones
            fig_hist.add_vline(x=tolerance, line_dash="dash", line_color="green", annotation_text=f"+{tolerance}%")
            fig_hist.add_vline(x=-tolerance, line_dash="dash", line_color="green", annotation_text=f"-{tolerance}%")
            
            st.plotly_chart(fig_hist, use_container_width=True)
        
        if show_scatter:
            st.subheader("📊 QTY vs RM Scatter Plot")
            st.markdown('<div class="graph-description">This scatter plot shows the relationship between current quantity (QTY) and required minimum quantity (RM IN QTY). Points above the diagonal line indicate excess inventory, while points below indicate shortages. The color coding helps identify status at a glance.</div>', unsafe_allow_html=True)
            
            qty_values = [item['QTY'] for item in processed_data]
            rm_values = [item['RM IN QTY'] for item in processed_data]
            status_values = [item['Status'] for item in processed_data]
            materials = [item['Material'] for item in processed_data]
            
            fig_scatter = px.scatter(
                x=rm_values,
                y=qty_values,
                color=status_values,
                color_discrete_map=analyzer.status_colors,
                hover_data={'Material': materials},
                title="QTY vs RM IN QTY Scatter Plot",
                labels={'x': 'RM IN QTY', 'y': 'Current QTY', 'color': 'Status'}
            )
            
            # Add diagonal line for reference
            max_val = max(max(qty_values), max(rm_values))
            fig_scatter.add_shape(
                type="line",
                x0=0, y0=0, x1=max_val, y1=max_val,
                line=dict(dash="dash", color="gray")
            )
            
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        if show_vendor_excess:
            st.subheader("🔵 Top 10 Vendor-wise Excess Inventory Parts")
            st.markdown('<div class="graph-description">This chart shows the top excess inventory parts grouped by vendor. It helps identify which vendors are contributing most to excess inventory, enabling targeted discussions about order quantities and delivery schedules.</div>', unsafe_allow_html=True)
            create_vendor_wise_top_parts_chart(processed_data, 'Excess Inventory', analyzer.status_colors['Excess Inventory'])
        
        if show_vendor_short:
            st.subheader("🔴 Top 10 Vendor-wise Short Inventory Parts")
            st.markdown('<div class="graph-description">This chart displays the top short inventory parts by vendor. It highlights which suppliers may need expedited orders or increased safety stock levels to prevent stockouts and production disruptions.</div>', unsafe_allow_html=True)
            create_vendor_wise_top_parts_chart(processed_data, 'Short Inventory', analyzer.status_colors['Short Inventory'])
        
        if show_vendor_normal:
            st.subheader("🟢 Top 10 Vendor-wise Within Norms Parts")
            st.markdown('<div class="graph-description">This chart shows the top parts within acceptable norms by vendor. It identifies which suppliers are providing consistent, well-managed inventory levels and can serve as benchmarks for vendor performance.</div>', unsafe_allow_html=True)
            create_vendor_wise_top_parts_chart(processed_data, 'Within Norms', analyzer.status_colors['Within Norms'])
    
    with tab2:
        st.header("🎯 3D Visualization")
        st.markdown('<div class="graph-description">This 3D scatter plot provides a comprehensive view of your inventory with QTY, RM IN QTY, and Stock Value as the three dimensions. The size of bubbles represents stock value, while colors indicate inventory status. This visualization helps identify high-value items that need attention.</div>', unsafe_allow_html=True)
        
        # Create 3D scatter plot
        fig_3d = px.scatter_3d(
            x=[item['QTY'] for item in processed_data],
            y=[item['RM IN QTY'] for item in processed_data],
            z=[item['Stock_Value'] for item in processed_data],
            color=[item['Status'] for item in processed_data],
            size=[item['Stock_Value'] for item in processed_data],
            hover_data={'Material': [item['Material'] for item in processed_data]},
            color_discrete_map=analyzer.status_colors,
            title="3D Inventory Analysis: QTY vs RM vs Stock Value",
            labels={'x': 'Current QTY', 'y': 'RM IN QTY', 'z': 'Stock Value', 'color': 'Status'}
        )
        
        fig_3d.update_layout(height=600)
        st.plotly_chart(fig_3d, use_container_width=True)
    
    with tab3:
        st.header("📋 Detailed Data Analysis")
        
        # Filter options
        col1, col2 = st.columns(2)
        
        with col1:
            status_filter = st.selectbox(
                "Filter by Status",
                options=['All'] + list(analyzer.status_colors.keys())
            )
        
        with col2:
            vendor_filter = st.selectbox(
                "Filter by Vendor",
                options=['All'] + vendors
            )
        
        # Apply filters
        filtered_data = processed_data.copy()
        
        if status_filter != 'All':
            filtered_data = [item for item in filtered_data if item['Status'] == status_filter]
        
        if vendor_filter != 'All':
            filtered_data = [item for item in filtered_data if item['Vendor'] == vendor_filter]
        
        # Create DataFrame for display
        display_df = pd.DataFrame(filtered_data)
        
        if not display_df.empty:
            # Format the DataFrame
            display_df['Variance_%'] = display_df['Variance_%'].round(2)
            display_df['Variance_Value'] = display_df['Variance_Value'].round(2)
            display_df['Stock_Value'] = display_df['Stock_Value'].apply(lambda x: f"₹{x:,}")
            
            st.subheader(f"📊 Filtered Data ({len(display_df)} items)")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Summary statistics for filtered data
            st.subheader("📈 Summary Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_variance = sum(item['Variance_%'] for item in filtered_data) / len(filtered_data)
                st.metric("Average Variance %", f"{avg_variance:.2f}%")
            
            with col2:
                total_filtered_value = sum(item['Stock_Value'] for item in filtered_data)
                st.metric("Total Stock Value", f"₹{total_filtered_value:,}")
            
            with col3:
                critical_items = len([item for item in filtered_data if abs(item['Variance_%']) > tolerance * 1.5])
                st.metric("Critical Items", critical_items)
        else:
            st.info("No data matches the selected filters.")
    
    with tab4:
        st.header("🏢 Detailed Vendor Analysis")
        
        # Vendor selection for detailed analysis
        selected_vendor_analysis = st.selectbox(
            "Select Vendor for Detailed Analysis",
            options=vendors,
            help="Choose a vendor to see detailed breakdown of their inventory status"
        )
        
        if selected_vendor_analysis:
            vendor_items = [item for item in processed_data if item['Vendor'] == selected_vendor_analysis]
            vendor_data = vendor_summary[selected_vendor_analysis]
            
            # Vendor overview
            st.subheader(f"📊 {selected_vendor_analysis} Overview")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Parts", vendor_data['total_parts'])
            
            with col2:
                st.metric("Total QTY", f"{vendor_data['total_qty']:.1f}")
            
            with col3:
                st.metric("Total RM", f"{vendor_data['total_rm']:.1f}")
            
            with col4:
                st.metric("Total Value", f"₹{vendor_data['total_value']:,}")
            
            # Status breakdown
            st.subheader("📈 Status Breakdown")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "🔴 Short Inventory",
                    f"{vendor_data['short_parts']} parts",
                    f"₹{vendor_data['short_value']:,}"
                )
            
            with col2:
                st.metric(
                    "🔵 Excess Inventory",
                    f"{vendor_data['excess_parts']} parts",
                    f"₹{vendor_data['excess_value']:,}"
                )
            
            with col3:
                st.metric(
                    "🟢 Within Norms",
                    f"{vendor_data['normal_parts']} parts",
                    f"₹{vendor_data['normal_value']:,}"
                )
            
            # Vendor-specific charts
            vendor_status_counts = {
                'Short Inventory': vendor_data['short_parts'],
                'Excess Inventory': vendor_data['excess_parts'],
                'Within Norms': vendor_data['normal_parts']
            }
            
            # Filter out zero values
            vendor_status_counts = {k: v for k, v in vendor_status_counts.items() if v > 0}
            
            if vendor_status_counts:
                fig_vendor_pie = px.pie(
                    values=list(vendor_status_counts.values()),
                    names=list(vendor_status_counts.keys()),
                    color=list(vendor_status_counts.keys()),
                    color_discrete_map=analyzer.status_colors,
                    title=f"{selected_vendor_analysis} - Status Distribution"
                )
                st.plotly_chart(fig_vendor_pie, use_container_width=True)
            
            # Detailed vendor data table
            st.subheader("📋 Detailed Item List")
            vendor_df = pd.DataFrame(vendor_items)
            vendor_df['Variance_%'] = vendor_df['Variance_%'].round(2)
            vendor_df['Variance_Value'] = vendor_df['Variance_Value'].round(2)
            vendor_df['Stock_Value'] = vendor_df['Stock_Value'].apply(lambda x: f"₹{x:,}")
            
            st.dataframe(vendor_df, use_container_width=True, hide_index=True)
    
    with tab5:
        st.header("📤 Export Options")
        
        # Export full data
        st.subheader("📊 Export Full Analysis")
        
        # Prepare export data
        export_df = pd.DataFrame(processed_data)
        export_df['Stock_Value_Formatted'] = export_df['Stock_Value'].apply(lambda x: f"₹{x:,}")
        
        # Convert to CSV
        csv = export_df.to_csv(index=False)
        
        st.download_button(
            label="📥 Download Full Analysis (CSV)",
            data=csv,
            file_name=f"inventory_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        # Export summary
        st.subheader("📈 Export Summary Report")
        
        summary_report = f"""
INVENTORY ANALYSIS SUMMARY REPORT
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Tolerance Zone: ±{tolerance}%

OVERALL SUMMARY:
- Total Items: {len(processed_data)}
- Total Stock Value: ₹{total_value:,}

STATUS BREAKDOWN:
- Within Norms: {summary_data['Within Norms']['count']} items (₹{summary_data['Within Norms']['value']:,})
- Excess Inventory: {summary_data['Excess Inventory']['count']} items (₹{summary_data['Excess Inventory']['value']:,})
- Short Inventory: {summary_data['Short Inventory']['count']} items (₹{summary_data['Short Inventory']['value']:,})

VENDOR SUMMARY:
"""
        
        for vendor, data in vendor_summary.items():
            summary_report += f"""
{vendor}:
  - Total Parts: {data['total_parts']}
  - Total Value: ₹{data['total_value']:,}
  - Short: {data['short_parts']} items
  - Excess: {data['excess_parts']} items
  - Normal: {data['normal_parts']} items
"""
        
        st.download_button(
            label="📥 Download Summary Report (TXT)",
            data=summary_report,
            file_name=f"inventory_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
        
        # Export filtered data based on current selections
        if selected_vendor != 'All Vendors':
            vendor_export_data = [item for item in processed_data if item['Vendor'] == selected_vendor]
            vendor_export_df = pd.DataFrame(vendor_export_data)
            vendor_csv = vendor_export_df.to_csv(index=False)
            
            st.subheader(f"🏢 Export {selected_vendor} Data")
            st.download_button(
                label=f"📥 Download {selected_vendor} Analysis (CSV)",
                data=vendor_csv,
                file_name=f"{selected_vendor}_inventory_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
