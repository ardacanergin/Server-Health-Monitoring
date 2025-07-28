graph TD
    A[Configuration Files] --> B[Config Loader]
    A1[servers.yaml/json] --> B
    A2[config.yaml] --> B
    A3[.env file] --> B
    
    B --> C[Main Controller]
    C --> D[Server Objects Creation]
    
    D --> E[ThreadPoolExecutor]
    E --> F1[Monitor Thread 1]
    E --> F2[Monitor Thread 2]
    E --> F3[Monitor Thread N]
    
    F1 --> G1[SSH Connection]
    F2 --> G2[SSH Connection]
    F3 --> G3[SSH Connection]
    
    G1 --> H1[Health Checks]
    G2 --> H2[Health Checks]
    G3 --> H3[Health Checks]
    
    H1 --> I1[Raw Data Collection]
    H2 --> I2[Raw Data Collection]
    H3 --> I3[Raw Data Collection]
    
    I1 --> J1[Data Parsing & Processing]
    I2 --> J2[Data Parsing & Processing]
    I3 --> J3[Data Parsing & Processing]
    
    J1 --> K1[Individual Report Generation]
    J2 --> K2[Individual Report Generation]
    J3 --> K3[Individual Report Generation]
    
    K1 --> L[Results Aggregation]
    K2 --> L
    K3 --> L
    
    L --> M[Combined Report Builder]
    M --> N1[Summary Table HTML]
    M --> N2[Director Summary HTML]
    M --> N3[Combined JSON Report]
    
    N1 --> O1[Per-Admin Email Distribution]
    N2 --> O2[Director Email]
    N3 --> O3[Ops Team Email]
    
    P[Failed Connections] --> Q[Alert Email Generation]
    Q --> R[Admin Notifications]
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style E fill:#e8f5e8
    style M fill:#fce4ec
    style O1 fill:#fff9c4
    style O2 fill:#fff9c4
    style O3 fill:#fff9c4