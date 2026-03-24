import dash
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
import pandas as pd
from dash import html, dcc, Input, Output
import datetime

df = pd.read_csv('./clinical_analytics.csv')

df['Wait Time Min'] = pd.to_numeric(df['Wait Time Min'], errors='coerce')
df['Care Score'] = pd.to_numeric(df['Care Score'], errors='coerce')
df = df.dropna(subset=['Wait Time Min', 'Care Score'])

# Convertir Check-In Time a datetime con formato especificado
df['Check-In Time'] = pd.to_datetime(df['Check-In Time'], format='%Y-%m-%d %I:%M:%S %p', errors='coerce')
df['Check-In Date'] = df['Check-In Time'].dt.date
df['Check-In Month'] = df['Check-In Time'].dt.to_period('M')

# Limpiar Admit Source - reemplazar NaN con "Unknown"
df['Admit Source'] = df['Admit Source'].fillna('Unknown')

negative_count = (df['Wait Time Min'] < 0).sum()
df = df[df['Wait Time Min'] >= 0]

app = dash.Dash(external_stylesheets=[dbc.themes.MATERIA])

app.layout = dbc.Container([
    dbc.NavbarSimple(
        brand="Dashboard de Analítica Clínica",
        color="primary",
        dark=True,
        className="mb-4"
    ),
    
    dbc.Alert(
        f"Nota: Se encontraron {negative_count} registros con tiempos de espera negativos (pacientes que llegaron tarde) y fueron excluidos del análisis.",
        color="warning",
        className="mb-3"
    ) if negative_count > 0 else html.Div(),
    
    # KPIs
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("Tiempo de Espera Promedio", className="card-title"),
                html.H2(id='avg-wait', className="text-success")
            ])
        ]), md=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("Care Score Promedio", className="card-title"),
                html.H2(id='avg-care-score', className="text-info")
            ])
        ]), md=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("Total de Registros", className="card-title"),
                html.H2(id='total-records', className="text-warning")
            ])
        ]), md=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("Clínicas Activas", className="card-title"),
                html.H2(id='active-clinics', className="text-primary")
            ])
        ]), md=3),
    ], className="mb-4"),
    
    # Filtros
    dbc.Row([
        dbc.Col([
            html.Label("Seleccionar Departamento:", className="fw-bold"),
            dcc.Dropdown(
                id="department-filter",
                options=[{'label': dept, 'value': dept} for dept in sorted(df['Department'].unique())],
                value=df['Department'].unique().tolist(),
                multi=True,
                className="mb-3"
            )
        ], md=3),
        
        dbc.Col([
            html.Label("Tipo de Admisión:", className="fw-bold"),
            dcc.Dropdown(
                id="admit-type-filter",
                options=[{'label': atype, 'value': atype} for atype in sorted(df['Admit Type'].unique())],
                value=df['Admit Type'].unique().tolist(),
                multi=True,
                className="mb-3"
            )
        ], md=3),
        
        # NUEVO FILTRO: Admit Source
        dbc.Col([
            html.Label("Fuente de Admisión:", className="fw-bold"),
            dcc.Dropdown(
                id="admit-source-filter",
                options=[{'label': source, 'value': source} for source in sorted(df['Admit Source'].unique())],
                value=df['Admit Source'].unique().tolist(),
                multi=True,
                className="mb-3"
            )
        ], md=3),
        
        dbc.Col([
            html.Label("Rango de Tiempo de Espera (min):", className="fw-bold"),
            dcc.RangeSlider(
                id="wait-time-filter",
                min=df['Wait Time Min'].min(),
                max=df['Wait Time Min'].max(),
                step=1,
                value=[df['Wait Time Min'].min(), df['Wait Time Min'].max()],
                marks={
                    int(df['Wait Time Min'].min()): f"{int(df['Wait Time Min'].min())}",
                    int(df['Wait Time Min'].max()//2): f"{int(df['Wait Time Min'].max()//2)}",
                    int(df['Wait Time Min'].max()): f"{int(df['Wait Time Min'].max())}"
                },
                tooltip={"placement": "bottom", "always_visible": True}
            )
        ], md=3)
    ], className="mb-4"),
    
    # Primera fila de gráficos
    dbc.Row([
        dbc.Col(dcc.Graph(id="scatter-plot"), md=6),
        dbc.Col(dcc.Graph(id="pie-plot"), md=6)
    ], className="mb-4"),
    
    # Segunda fila de gráficos
    dbc.Row([
        dbc.Col(dcc.Graph(id="histogram-plot"), md=6),
        # NUEVO GRÁFICO: Volumen de pacientes en el tiempo
        dbc.Col(dcc.Graph(id="timeline-plot"), md=6)
    ], className="mb-4"),
    
    # NUEVO: Gráfico de barras por Admit Source
    dbc.Row([
        dbc.Col(dcc.Graph(id="admit-source-bar"), md=12)
    ], className="mb-4")
    
], fluid=True)

@app.callback(
    [
        Output("scatter-plot", "figure"),
        Output("pie-plot", "figure"),
        Output("histogram-plot", "figure"),
        Output("timeline-plot", "figure"),
        Output("admit-source-bar", "figure"),
        Output("avg-wait", "children"),
        Output("avg-care-score", "children"),
        Output("total-records", "children"),
        Output("active-clinics", "children"),
    ],
    [
        Input("department-filter", "value"),
        Input("admit-type-filter", "value"),
        Input("admit-source-filter", "value"),
        Input("wait-time-filter", "value")
    ]
)
def update_dashboard(departments, admit_types, admit_sources, wait_range):
    # Filtrar datos
    dff = df[
        (df['Department'].isin(departments)) & 
        (df['Admit Type'].isin(admit_types)) &
        (df['Admit Source'].isin(admit_sources)) &
        (df['Wait Time Min'].between(wait_range[0], wait_range[1]))
    ]
    
    # Gráfico 1: Scatter plot
    scatter = px.scatter(
        dff, 
        x="Wait Time Min", 
        y="Care Score",
        color="Department",
        size="Care Score",
        hover_data=['Clinic Name', 'Encounter Status', 'Admit Source'],
        title="Tiempo de Espera vs. Care Score por Departamento",
        labels={
            "Wait Time Min": "Tiempo de Espera (min)",
            "Care Score": "Puntuación de Atención"
        }
    )
    scatter.update_layout(height=400)
    
    # Gráfico 2: Pie chart de departamentos
    dept_counts = dff['Department'].value_counts().reset_index()
    dept_counts.columns = ['Department', 'Count']
    
    pie = px.pie(
        dept_counts,
        names="Department",
        values="Count",
        title="Distribución de Casos por Departamento",
        hole=0.3
    )
    pie.update_layout(height=400)
    
    # Gráfico 3: Histograma de tiempos de espera
    histogram = px.histogram(
        dff,
        x="Wait Time Min",
        nbins=30,
        color="Encounter Status",
        title="Distribución de Tiempos de Espera",
        labels={"Wait Time Min": "Tiempo de Espera (min)", "count": "Frecuencia"},
        marginal="box"
    )
    histogram.update_layout(height=400)
    
    # NUEVO Gráfico 4: Timeline de volumen de pacientes
    timeline_df = dff.groupby('Check-In Month').size().reset_index(name='Cantidad')
    timeline_df['Check-In Month'] = timeline_df['Check-In Month'].astype(str)
    
    timeline = px.line(
        timeline_df,
        x='Check-In Month',
        y='Cantidad',
        title='Volumen de Pacientes por Mes',
        labels={'Check-In Month': 'Mes', 'Cantidad': 'Número de Pacientes'},
        markers=True
    )
    timeline.update_traces(line_color='#17a2b8', line_width=3)
    timeline.update_layout(
        height=400,
        xaxis_tickangle=-45,
        hovermode='x unified'
    )
    
    # NUEVO Gráfico 5: Barras de Admit Source con tiempo promedio de espera
    admit_source_stats = dff.groupby('Admit Source').agg({
        'Wait Time Min': 'mean',
        'Encounter Number': 'count'
    }).reset_index()
    admit_source_stats.columns = ['Admit Source', 'Tiempo Promedio', 'Total Casos']
    admit_source_stats = admit_source_stats.sort_values('Tiempo Promedio', ascending=False)
    
    admit_bar = go.Figure()
    admit_bar.add_trace(go.Bar(
        x=admit_source_stats['Admit Source'],
        y=admit_source_stats['Tiempo Promedio'],
        name='Tiempo Promedio de Espera',
        marker=dict(
        color=admit_source_stats['Tiempo Promedio'],
        colorscale='Viridis', 
        showscale=False),
        text=admit_source_stats['Tiempo Promedio'].round(1),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Tiempo Promedio: %{y:.1f} min<br>Total Casos: %{customdata}<extra></extra>',
        customdata=admit_source_stats['Total Casos']
    ))
    
    admit_bar.update_layout(
        title='Tiempo Promedio de Espera por Fuente de Admisión',
        xaxis_title='Fuente de Admisión',
        yaxis_title='Tiempo Promedio de Espera (min)',
        height=800,
        xaxis_tickangle=-45,
        showlegend=False
    )
    
    # KPIs
    avg_wait = f"{dff['Wait Time Min'].mean():.1f} min" if not dff.empty else "No hay datos"
    avg_care = f"{dff['Care Score'].mean():.2f}" if not dff.empty else "No hay datos"
    total_records = f"{len(dff):,}" if not dff.empty else "0"
    active_clinics = f"{dff['Clinic Name'].nunique()}" if not dff.empty else "0"
    
    return scatter, pie, histogram, timeline, admit_bar, avg_wait, avg_care, total_records, active_clinics


if __name__ == '__main__':
    app.run(debug=True, port=8060)
