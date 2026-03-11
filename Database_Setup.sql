-- ============================================================
-- FinanceIQ  —  Database_Setup.sql  (v2 — Full Rebuild)
-- SQL Server Express  ·  FinanceIQ database
--
-- Changes from v1:
--   - Added goals table
--   - Added tags column to transactions
--   - Added carry_forward columns to budgets
--   - Budget month_year uses first-of-month DATE
--   - Default budgets for 35+ categories
--
-- HOW TO RUN
--   SSMS  : Open file → press F5
--   sqlcmd: sqlcmd -S localhost\SQLExpress -d FinanceIQ -i Database_Setup.sql
-- ============================================================

USE FinanceIQ;
GO


-- ════════════════════════════════════════════════════════════
-- SECTION 0  —  DROP ALL TABLES  (reverse FK order)
-- ════════════════════════════════════════════════════════════
IF OBJECT_ID('dbo.goals',               'U') IS NOT NULL DROP TABLE goals;
IF OBJECT_ID('dbo.split_transactions',  'U') IS NOT NULL DROP TABLE split_transactions;
IF OBJECT_ID('dbo.budgets',             'U') IS NOT NULL DROP TABLE budgets;
IF OBJECT_ID('dbo.categorization_rules','U') IS NOT NULL DROP TABLE categorization_rules;
IF OBJECT_ID('dbo.transactions',        'U') IS NOT NULL DROP TABLE transactions;
IF OBJECT_ID('dbo.accounts',            'U') IS NOT NULL DROP TABLE accounts;
IF OBJECT_ID('dbo.child_categories',    'U') IS NOT NULL DROP TABLE child_categories;
IF OBJECT_ID('dbo.parent_categories',   'U') IS NOT NULL DROP TABLE parent_categories;
GO


-- ════════════════════════════════════════════════════════════
-- SECTION 1  —  CREATE TABLES
-- ════════════════════════════════════════════════════════════

CREATE TABLE parent_categories (
    id        INT           IDENTITY(1,1) PRIMARY KEY,
    name      NVARCHAR(100) NOT NULL UNIQUE,
    color     NVARCHAR(7),
    icon      NVARCHAR(10),
    is_income BIT           DEFAULT 0
);
GO

CREATE TABLE child_categories (
    id        INT           IDENTITY(1,1) PRIMARY KEY,
    parent_id INT           NOT NULL
              CONSTRAINT FK_Child_Parent
              REFERENCES parent_categories(id) ON DELETE CASCADE,
    name      NVARCHAR(100) NOT NULL,
    color     NVARCHAR(7),
    icon      NVARCHAR(10),
    is_income BIT           DEFAULT 0
);
GO

CREATE TABLE accounts (
    id             INT           IDENTITY(1,1) PRIMARY KEY,
    name           NVARCHAR(255) NOT NULL,
    institution    NVARCHAR(255) NOT NULL,
    type           NVARCHAR(50)  NOT NULL,
    account_number NVARCHAR(100) NULL,
    currency       NVARCHAR(10)  DEFAULT 'CAD',
    balance        DECIMAL(18,2) DEFAULT 0.0,
    created_at     DATETIME2     DEFAULT GETDATE(),
    CONSTRAINT UQ_Account UNIQUE (institution, account_number)
);
GO

CREATE TABLE transactions (
    id                      INT           IDENTITY(1,1) PRIMARY KEY,
    account_id              INT           NOT NULL
                            CONSTRAINT FK_Txn_Account  REFERENCES accounts(id),
    date                    DATE          NOT NULL,
    description             NVARCHAR(500) NOT NULL,
    original_desc           NVARCHAR(500),
    amount                  DECIMAL(18,2) NOT NULL,
    parent_category_id      INT           NULL
                            CONSTRAINT FK_Txn_Parent   REFERENCES parent_categories(id),
    child_category_id       INT           NULL
                            CONSTRAINT FK_Txn_Child    REFERENCES child_categories(id),
    memo                    NVARCHAR(MAX),
    is_split                BIT           NOT NULL DEFAULT 0,
    is_transfer             BIT           NOT NULL DEFAULT 0,
    transfer_to_account_id  INT           NULL
                            CONSTRAINT FK_Txn_XferAcct REFERENCES accounts(id),
    transfer_investment_cat NVARCHAR(100) NULL,
    cleared                 BIT           NOT NULL DEFAULT 1,
    currency                NVARCHAR(10)  DEFAULT 'CAD',
    tags                    NVARCHAR(MAX),
    ai_confidence           DECIMAL(5,2)  DEFAULT 0.0,
    hash                    NVARCHAR(100) UNIQUE,
    imported_at             DATETIME2     DEFAULT GETDATE()
);
GO

CREATE TABLE split_transactions (
    id                INT           IDENTITY(1,1) PRIMARY KEY,
    transaction_id    INT           NOT NULL
                      CONSTRAINT FK_Split_Txn REFERENCES transactions(id) ON DELETE CASCADE,
    child_category_id INT           NOT NULL
                      CONSTRAINT FK_Split_Cat REFERENCES child_categories(id),
    amount            DECIMAL(18,2) NOT NULL,
    memo              NVARCHAR(MAX)
);
GO

CREATE TABLE categorization_rules (
    id                INT           IDENTITY(1,1) PRIMARY KEY,
    pattern           NVARCHAR(255) NOT NULL,
    child_category_id INT           NOT NULL
                      CONSTRAINT FK_Rule_Cat REFERENCES child_categories(id),
    match_type        NVARCHAR(50)  DEFAULT 'contains',
    priority          INT           DEFAULT 0,
    use_count         INT           DEFAULT 0,
    created_at        DATETIME2     DEFAULT GETDATE()
);
GO

CREATE TABLE budgets (
    id                  INT           IDENTITY(1,1) PRIMARY KEY,
    child_category_id   INT           NOT NULL
                        CONSTRAINT FK_Budget_Cat REFERENCES child_categories(id),
    month_year          DATE          NOT NULL DEFAULT CAST(GETDATE() AS DATE),
    amount              DECIMAL(18,2) NOT NULL,
    carry_forward       BIT           DEFAULT 0,
    carry_forward_type  NVARCHAR(50)  DEFAULT 'none',  -- none / underspent / overspent / both
    CONSTRAINT UQ_Budget_Month UNIQUE (child_category_id, month_year)
);
GO

CREATE TABLE goals (
    id              INT           IDENTITY(1,1) PRIMARY KEY,
    name            NVARCHAR(255) NOT NULL,
    goal_type       NVARCHAR(50)  DEFAULT 'total',   -- 'total' or 'monthly'
    target_amount   DECIMAL(18,2) NOT NULL,
    monthly_amount  DECIMAL(18,2) NULL,
    target_date     DATE          NULL,
    account_id      INT           NULL
                    CONSTRAINT FK_Goal_Account REFERENCES accounts(id) ON DELETE SET NULL,
    created_at      DATETIME2     DEFAULT GETDATE()
);
GO


-- ════════════════════════════════════════════════════════════
-- SECTION 2  —  PARENT CATEGORIES  (21 parents)
-- ════════════════════════════════════════════════════════════
INSERT INTO parent_categories (name, color, icon, is_income) VALUES
('Income',            '#22c55e', N'💵', 1),
('Housing',           '#3b82f6', N'🏠', 0),
('Utilities',         '#0ea5e9', N'💡', 0),
('Food & Dining',     '#f59e0b', N'🍽️', 0),
('Transportation',    '#8b5cf6', N'🚗', 0),
('Health & Medical',  '#ef4444', N'🏥', 0),
('Personal Care',     '#a78bfa', N'🧴', 0),
('Shopping',          '#ec4899', N'🛍️', 0),
('Entertainment',     '#06b6d4', N'🎬', 0),
('Travel',            '#14b8a6', N'✈️', 0),
('Education',         '#fbbf24', N'📚', 0),
('Children & Family', '#fb923c', N'👶', 0),
('Pets',              '#84cc16', N'🐾', 0),
('Gifts & Donations', '#f87171', N'🎁', 0),
('Subscriptions',     '#7c3aed', N'📱', 0),
('Cell Phone',        '#0284c7', N'📱', 0),
('Financial',         '#64748b', N'💳', 0),
('Investments',       '#10b981', N'📈', 0),
('Taxes',             '#dc2626', N'🏛️', 0),
('Business Expenses', '#78716c', N'🏢', 0),
('Uncategorized',     '#6b7280', N'❓', 0);
GO


-- ════════════════════════════════════════════════════════════
-- SECTION 3  —  CHILD CATEGORIES
-- ════════════════════════════════════════════════════════════

-- Income
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Salary & Wages','#15803d',N'💰',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Employment Income','#1a9850',N'💼',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Bonus & Commission','#14532d',N'🏆',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Freelance','#22c55e',N'💻',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Dividends','#4ade80',N'💹',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Interest Income','#16a34a',N'🏦',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Capital Gains','#15803d',N'📊',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Rental Income','#166534',N'🏠',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'CPP / OAS','#34d399',N'🇨🇦',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'EI Benefits','#10b981',N'🤝',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Child Benefits (CCB)','#059669',N'👶',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Tax Refund','#047857',N'📋',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Other Income','#6b7280',N'💰',1 FROM parent_categories WHERE name='Income';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Personal Income','#22c55e',N'💵',1 FROM parent_categories WHERE name='Income';
GO

-- Housing
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Mortgage','#2563eb',N'🏦',0 FROM parent_categories WHERE name='Housing';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Rent','#60a5fa',N'🔑',0 FROM parent_categories WHERE name='Housing';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Property Tax','#3b82f6',N'🏛️',0 FROM parent_categories WHERE name='Housing';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Home Insurance','#2563eb',N'🛡️',0 FROM parent_categories WHERE name='Housing';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Condo Fees / HOA','#1d4ed8',N'🏢',0 FROM parent_categories WHERE name='Housing';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Home Maintenance','#1e40af',N'🔧',0 FROM parent_categories WHERE name='Housing';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Furniture & Decor','#bfdbfe',N'🛋️',0 FROM parent_categories WHERE name='Housing';
GO

-- Utilities
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Electricity','#0284c7',N'⚡',0 FROM parent_categories WHERE name='Utilities';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Natural Gas / Heat','#0369a1',N'🔥',0 FROM parent_categories WHERE name='Utilities';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Water & Sewer','#075985',N'💧',0 FROM parent_categories WHERE name='Utilities';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Internet','#0c4a6e',N'🌐',0 FROM parent_categories WHERE name='Utilities';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Cable / Satellite TV','#082f49',N'📡',0 FROM parent_categories WHERE name='Utilities';
GO

-- Food & Dining
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Groceries','#d97706',N'🛒',0 FROM parent_categories WHERE name='Food & Dining';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Restaurants','#b45309',N'🍴',0 FROM parent_categories WHERE name='Food & Dining';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Fast Food','#92400e',N'🍔',0 FROM parent_categories WHERE name='Food & Dining';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Coffee & Cafes','#78350f',N'☕',0 FROM parent_categories WHERE name='Food & Dining';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Alcohol & LCBO','#c2410c',N'🍷',0 FROM parent_categories WHERE name='Food & Dining';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Food Delivery','#f97316',N'🛵',0 FROM parent_categories WHERE name='Food & Dining';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Dining & Drinks','#b45309',N'🍽️',0 FROM parent_categories WHERE name='Food & Dining';
GO

-- Transportation
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Gas & Fuel','#7c3aed',N'⛽',0 FROM parent_categories WHERE name='Transportation';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Car Insurance','#6d28d9',N'🛡️',0 FROM parent_categories WHERE name='Transportation';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Car Payment','#5b21b6',N'🚘',0 FROM parent_categories WHERE name='Transportation';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Car Maintenance','#4c1d95',N'🔩',0 FROM parent_categories WHERE name='Transportation';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Parking','#a855f7',N'🅿️',0 FROM parent_categories WHERE name='Transportation';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Tolls & 407','#c084fc',N'🛣️',0 FROM parent_categories WHERE name='Transportation';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Public Transit','#d8b4fe',N'🚌',0 FROM parent_categories WHERE name='Transportation';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Taxi & Rideshare','#e9d5ff',N'🚕',0 FROM parent_categories WHERE name='Transportation';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Auto & Transport','#7c3aed',N'🚗',0 FROM parent_categories WHERE name='Transportation';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Car Wash','#9333ea',N'🚿',0 FROM parent_categories WHERE name='Transportation';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Service & Parts','#6d28d9',N'🔧',0 FROM parent_categories WHERE name='Transportation';
GO

-- Health & Medical
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Doctor & Specialists','#dc2626',N'👨‍⚕️',0 FROM parent_categories WHERE name='Health & Medical';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Dentist','#b91c1c',N'🦷',0 FROM parent_categories WHERE name='Health & Medical';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Optometrist & Vision','#991b1b',N'👓',0 FROM parent_categories WHERE name='Health & Medical';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Pharmacy','#7f1d1d',N'💊',0 FROM parent_categories WHERE name='Health & Medical';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Mental Health','#fca5a5',N'🧠',0 FROM parent_categories WHERE name='Health & Medical';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Physiotherapy','#f87171',N'🦴',0 FROM parent_categories WHERE name='Health & Medical';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Health Insurance','#b91c1c',N'🛡️',0 FROM parent_categories WHERE name='Health & Medical';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Gym & Fitness','#991b1b',N'🏋️',0 FROM parent_categories WHERE name='Health & Medical';
GO

-- Personal Care
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Hair & Salon','#8b5cf6',N'💇',0 FROM parent_categories WHERE name='Personal Care';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Spa & Massage','#7c3aed',N'💆',0 FROM parent_categories WHERE name='Personal Care';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Cosmetics & Beauty','#6d28d9',N'💄',0 FROM parent_categories WHERE name='Personal Care';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Clothing & Apparel','#5b21b6',N'👕',0 FROM parent_categories WHERE name='Personal Care';
GO

-- Shopping
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Amazon','#db2777',N'📦',0 FROM parent_categories WHERE name='Shopping';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Electronics & Tech','#be185d',N'📱',0 FROM parent_categories WHERE name='Shopping';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Home Goods','#f9a8d4',N'🏡',0 FROM parent_categories WHERE name='Shopping';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Department Stores','#f472b6',N'🏬',0 FROM parent_categories WHERE name='Shopping';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Online Shopping','#ec4899',N'🖥️',0 FROM parent_categories WHERE name='Shopping';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Warehouse Clubs','#db2777',N'🏪',0 FROM parent_categories WHERE name='Shopping';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Shopping','#ec4899',N'🛍️',0 FROM parent_categories WHERE name='Shopping';
GO

-- Entertainment
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Streaming Services','#0891b2',N'📺',0 FROM parent_categories WHERE name='Entertainment';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Movies & Cinema','#0e7490',N'🎥',0 FROM parent_categories WHERE name='Entertainment';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Concerts & Events','#155e75',N'🎤',0 FROM parent_categories WHERE name='Entertainment';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Books & Magazines','#67e8f9',N'📚',0 FROM parent_categories WHERE name='Entertainment';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Hobbies & Crafts','#22d3ee',N'🎯',0 FROM parent_categories WHERE name='Entertainment';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Gaming','#06b6d4',N'🎮',0 FROM parent_categories WHERE name='Entertainment';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Entertainment','#06b6d4',N'🎬',0 FROM parent_categories WHERE name='Entertainment';
GO

-- Travel
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Flights','#0f766e',N'🛫',0 FROM parent_categories WHERE name='Travel';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Hotels & Accommodation','#0d9488',N'🏨',0 FROM parent_categories WHERE name='Travel';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Travel Insurance','#115e59',N'🛡️',0 FROM parent_categories WHERE name='Travel';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Car Rental','#134e4a',N'🚙',0 FROM parent_categories WHERE name='Travel';
GO

-- Education
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Tuition & Fees','#f59e0b',N'🎓',0 FROM parent_categories WHERE name='Education';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Textbooks & Supplies','#b45309',N'📝',0 FROM parent_categories WHERE name='Education';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Online Courses','#92400e',N'💻',0 FROM parent_categories WHERE name='Education';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Student Loans','#78350f',N'📖',0 FROM parent_categories WHERE name='Education';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Education','#f59e0b',N'📚',0 FROM parent_categories WHERE name='Education';
GO

-- Children & Family
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Childcare & Daycare','#f97316',N'🧒',0 FROM parent_categories WHERE name='Children & Family';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Baby Supplies','#ea580c',N'🍼',0 FROM parent_categories WHERE name='Children & Family';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Kids Activities','#c2410c',N'⚽',0 FROM parent_categories WHERE name='Children & Family';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Toys & Games','#9a3412',N'🧸',0 FROM parent_categories WHERE name='Children & Family';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Kids','#fb923c',N'👧',0 FROM parent_categories WHERE name='Children & Family';
GO

-- Pets
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Pet Food','#65a30d',N'🦴',0 FROM parent_categories WHERE name='Pets';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Vet & Medical','#4d7c0f',N'🐶',0 FROM parent_categories WHERE name='Pets';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Pet Insurance','#3f6212',N'🛡️',0 FROM parent_categories WHERE name='Pets';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Pet Grooming','#365314',N'✂️',0 FROM parent_categories WHERE name='Pets';
GO

-- Gifts & Donations
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Gifts Given','#ef4444',N'🎀',0 FROM parent_categories WHERE name='Gifts & Donations';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Charitable Donations','#dc2626',N'❤️',0 FROM parent_categories WHERE name='Gifts & Donations';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Religious Donations','#b91c1c',N'⛪',0 FROM parent_categories WHERE name='Gifts & Donations';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Charity & Donations','#ef4444',N'🎁',0 FROM parent_categories WHERE name='Gifts & Donations';
GO

-- Subscriptions
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Streaming Video','#6d28d9',N'📺',0 FROM parent_categories WHERE name='Subscriptions';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Streaming Music','#5b21b6',N'🎵',0 FROM parent_categories WHERE name='Subscriptions';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Software & SaaS','#4c1d95',N'💻',0 FROM parent_categories WHERE name='Subscriptions';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'News & Magazines','#3b0764',N'📰',0 FROM parent_categories WHERE name='Subscriptions';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Gaming Subscriptions','#7c3aed',N'🎮',0 FROM parent_categories WHERE name='Subscriptions';
GO

-- Cell Phone
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Monthly Plan','#0369a1',N'📡',0 FROM parent_categories WHERE name='Cell Phone';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Device Payments','#075985',N'📱',0 FROM parent_categories WHERE name='Cell Phone';
GO

-- Financial
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Credit Card Payment','#475569',N'💳',0 FROM parent_categories WHERE name='Financial';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Bank Fees','#334155',N'🏦',0 FROM parent_categories WHERE name='Financial';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Interest Charges','#1e293b',N'📊',0 FROM parent_categories WHERE name='Financial';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Transfer','#94a3b8',N'↔️',0 FROM parent_categories WHERE name='Financial';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Personal Loan','#64748b',N'💰',0 FROM parent_categories WHERE name='Financial';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Line of Credit','#94a3b8',N'📄',0 FROM parent_categories WHERE name='Financial';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Fees & Charges','#475569',N'💸',0 FROM parent_categories WHERE name='Financial';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Balance Adjustment','#64748b',N'⚖️',0 FROM parent_categories WHERE name='Financial';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Cash & ATM','#94a3b8',N'💵',0 FROM parent_categories WHERE name='Financial';
GO

-- Investments
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'RRSP','#059669',N'🏦',0 FROM parent_categories WHERE name='Investments';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'TFSA','#047857',N'💹',0 FROM parent_categories WHERE name='Investments';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'RESP','#065f46',N'🎓',0 FROM parent_categories WHERE name='Investments';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Stocks','#22c55e',N'📈',0 FROM parent_categories WHERE name='Investments';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'ETFs','#16a34a',N'💹',0 FROM parent_categories WHERE name='Investments';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Bonds','#15803d',N'📉',0 FROM parent_categories WHERE name='Investments';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Crypto','#166534',N'₿',0 FROM parent_categories WHERE name='Investments';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'GICs & Term Deposits','#14532d',N'🔒',0 FROM parent_categories WHERE name='Investments';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Pension Contributions','#166534',N'🏦',0 FROM parent_categories WHERE name='Investments';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Robo-Advisor','#16a34a',N'🤖',0 FROM parent_categories WHERE name='Investments';
GO

-- Taxes
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Federal Income Tax','#b91c1c',N'🇨🇦',0 FROM parent_categories WHERE name='Taxes';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Provincial Tax','#991b1b',N'🏛️',0 FROM parent_categories WHERE name='Taxes';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Tax Preparation','#ef4444',N'📋',0 FROM parent_categories WHERE name='Taxes';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'HST / GST Remittance','#dc2626',N'💰',0 FROM parent_categories WHERE name='Taxes';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Taxes','#dc2626',N'🏛️',0 FROM parent_categories WHERE name='Taxes';
GO

-- Business Expenses
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Office Supplies','#57534e',N'🖊️',0 FROM parent_categories WHERE name='Business Expenses';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Business Travel','#44403c',N'✈️',0 FROM parent_categories WHERE name='Business Expenses';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Client Entertainment','#292524',N'🍽️',0 FROM parent_categories WHERE name='Business Expenses';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Accounting & Legal','#57534e',N'⚖️',0 FROM parent_categories WHERE name='Business Expenses';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Business Insurance','#78716c',N'🛡️',0 FROM parent_categories WHERE name='Business Expenses';
GO

-- Uncategorized (fallback)
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Uncategorized','#6b7280',N'❓',0 FROM parent_categories WHERE name='Uncategorized';
INSERT INTO child_categories (parent_id,name,color,icon,is_income) SELECT id,'Uncategorized Item','#6b7280',N'❓',0 FROM parent_categories WHERE name='Uncategorized';
GO


-- ════════════════════════════════════════════════════════════
-- SECTION 4  —  DEFAULT BUDGETS (effective from 2024-01-01)
-- ════════════════════════════════════════════════════════════

DECLARE @eff DATE = '2024-01-01';

-- Housing
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,1800.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Housing' AND c.name='Mortgage';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,200.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Housing' AND c.name='Property Tax';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,150.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Housing' AND c.name='Home Insurance';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,100.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Housing' AND c.name='Home Maintenance';

-- Utilities
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,100.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Utilities' AND c.name='Electricity';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,80.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Utilities' AND c.name='Natural Gas / Heat';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,50.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Utilities' AND c.name='Water & Sewer';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,80.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Utilities' AND c.name='Internet';

-- Food & Dining
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,600.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Food & Dining' AND c.name='Groceries';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,150.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Food & Dining' AND c.name='Restaurants';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,80.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Food & Dining' AND c.name='Fast Food';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,60.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Food & Dining' AND c.name='Coffee & Cafes';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,50.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Food & Dining' AND c.name='Food Delivery';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,50.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Food & Dining' AND c.name='Alcohol & LCBO';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,150.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Food & Dining' AND c.name='Dining & Drinks';

-- Transportation
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,150.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Transportation' AND c.name='Gas & Fuel';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,200.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Transportation' AND c.name='Car Insurance';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,400.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Transportation' AND c.name='Car Payment';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,75.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Transportation' AND c.name='Car Maintenance';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,100.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Transportation' AND c.name='Public Transit';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,40.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Transportation' AND c.name='Parking';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,30.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Transportation' AND c.name='Taxi & Rideshare';

-- Health & Medical
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,50.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Health & Medical' AND c.name='Doctor & Specialists';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,50.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Health & Medical' AND c.name='Dentist';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,40.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Health & Medical' AND c.name='Pharmacy';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,100.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Health & Medical' AND c.name='Health Insurance';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,50.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Health & Medical' AND c.name='Gym & Fitness';

-- Personal Care
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,60.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Personal Care' AND c.name='Hair & Salon';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,30.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Personal Care' AND c.name='Cosmetics & Beauty';

-- Shopping
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,100.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Shopping' AND c.name='Amazon';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,75.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Shopping' AND c.name='Online Shopping';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,50.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Shopping' AND c.name='Electronics & Tech';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,150.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Shopping' AND c.name='Shopping';

-- Entertainment
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,60.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Entertainment' AND c.name='Movies & Cinema';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,75.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Entertainment' AND c.name='Concerts & Events';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,30.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Entertainment' AND c.name='Hobbies & Crafts';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,100.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Entertainment' AND c.name='Entertainment';

-- Cell Phone
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,60.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Cell Phone' AND c.name='Monthly Plan';

-- Subscriptions
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,25.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Subscriptions' AND c.name='Streaming Video';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,12.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Subscriptions' AND c.name='Streaming Music';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,20.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Subscriptions' AND c.name='Software & SaaS';

-- Financial
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,20.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Financial' AND c.name='Bank Fees';

-- Investments
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,500.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Investments' AND c.name='RRSP';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,300.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Investments' AND c.name='TFSA';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,200.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Investments' AND c.name='RESP';

-- Gifts & Donations
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,50.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Gifts & Donations' AND c.name='Gifts Given';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,50.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Gifts & Donations' AND c.name='Charitable Donations';

-- Children & Family
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,800.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Children & Family' AND c.name='Childcare & Daycare';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,100.00 FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Children & Family' AND c.name='Kids Activities';
INSERT INTO budgets (child_category_id,month_year,amount) SELECT c.id,@eff,50.00  FROM child_categories c JOIN parent_categories p ON c.parent_id=p.id WHERE p.name='Children & Family' AND c.name='Kids';
GO


-- ════════════════════════════════════════════════════════════
-- DONE
-- ════════════════════════════════════════════════════════════
PRINT '============================================================';
PRINT 'FinanceIQ v2 — database setup complete.';
PRINT '';
PRINT 'Tables    : 8 (added goals)';
PRINT 'Categories: 21 parents / 100+ children';
PRINT 'Budgets   : 45 defaults effective 2024-01-01';
PRINT '';
PRINT 'Next: streamlit run app.py';
PRINT '============================================================';
GO
