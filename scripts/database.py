# scripts/database.py
import oracledb
import pandas as pd
import logging
import sys
from datetime import datetime
import csv
import os
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_tables(connection):
    try:
        with connection.cursor() as cursor:
            # Create banks table
            cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE TABLE banks (
                        bank_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        name VARCHAR2(100) NOT NULL UNIQUE
                    )';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -955 THEN
                            RAISE;
                        END IF;
                END;
            """)
            
            # Create reviews table
            cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE TABLE reviews (
                        review_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        bank_id NUMBER NOT NULL,
                        content CLOB NOT NULL,
                        clean_content CLOB,
                        rating NUMBER(1) NOT NULL,
                        review_date DATE NOT NULL,
                        source VARCHAR2(50) DEFAULT ''Google Play'',
                        sentiment VARCHAR2(10),
                        sentiment_score NUMBER,
                        themes VARCHAR2(500),
                        CONSTRAINT fk_bank FOREIGN KEY (bank_id) REFERENCES banks(bank_id)
                    )';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -955 THEN
                            RAISE;
                        END IF;
                END;
            """)
            connection.commit()
            logging.info("Database tables created/verified")
            return True
    except Exception as e:
        logging.error(f"Error creating tables: {str(e)}")
        return False

def load_data_via_sqlldr(df):
    """Load data using SQL*Loader"""
    try:
        # Create CSV file
        csv_path = "oracle_load.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(['bank_name', 'content', 'clean_content', 'rating', 
                             'review_date', 'source', 'sentiment', 'sentiment_score', 'themes'])
            
            # Write data with robust type handling
            for _, row in df.iterrows():
                # Convert all values to strings first
                bank_name = str(row['bank'])
                content = str(row['review'])
                clean_content = str(row['clean_review'])
                rating = str(row['rating'])
                review_date = str(row['date'])
                source = str(row['source'])
                sentiment = str(row['sentiment'])
                sentiment_score = str(row['sentiment_score'])
                
                # Handle themes conversion
                if isinstance(row['themes'], list):
                    themes = ','.join(row['themes'])
                else:
                    themes = str(row['themes'])
                
                writer.writerow([
                    bank_name,
                    content[:4000],  # Truncate after conversion
                    clean_content[:4000],
                    rating,
                    review_date,
                    source,
                    sentiment,
                    sentiment_score,
                    themes[:500]  # Truncate after conversion
                ])
        
        # Create control file
        with open('load.ctl', 'w') as ctl:
            ctl.write(f"""
                LOAD DATA
                INFILE '{csv_path}'
                APPEND
                INTO TABLE reviews
                FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
                TRAILING NULLCOLS
                (
                    bank_name CHAR(100),
                    content CHAR(4000),
                    clean_content CHAR(4000),
                    rating INTEGER EXTERNAL,
                    review_date DATE "YYYY-MM-DD",
                    source CHAR(50),
                    sentiment CHAR(10),
                    sentiment_score DECIMAL EXTERNAL,
                    themes CHAR(500)
                )
            """)
        
        # Create SQL script for bank mapping
        with open('post_load.sql', 'w') as sql:
            sql.write("""
                UPDATE reviews r
                SET bank_id = (
                    SELECT bank_id FROM banks b 
                    WHERE b.name = r.bank_name
                )
                WHERE bank_id IS NULL;
                
                ALTER TABLE reviews DROP COLUMN bank_name;
            """)
        
        # Execute SQL*Loader
        sqlldr_cmd = f'sqlldr userid=system/admin@localhost:1521/XEPDB1 control=load.ctl'
        result = subprocess.run(sqlldr_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"SQL*Loader failed with return code {result.returncode}")
            logging.error(f"SQL*Loader stdout: {result.stdout[:1000]}")
            logging.error(f"SQL*Loader stderr: {result.stderr[:1000]}")
            return False
        
        logging.info("SQL*Loader completed successfully")
        
        # Execute post-load SQL
        with oracledb.connect(user="system", password="admin", dsn="localhost:1521/XEPDB1") as conn:
            with conn.cursor() as cursor:
                with open('post_load.sql') as f:
                    sql_commands = f.read().split(';')
                    for cmd in sql_commands:
                        if cmd.strip():
                            try:
                                cursor.execute(cmd)
                            except Exception as e:
                                logging.warning(f"SQL execution warning: {str(e)}")
                conn.commit()
        
        logging.info("Post-load SQL executed")
        return True
        
    except Exception as e:
        logging.error(f"SQL*Loader process failed: {str(e)}", exc_info=True)
        return False

def insert_data_pure_python(connection, df):
    """Fallback insertion method using pure Python"""
    try:
        with connection.cursor() as cursor:
            # Get bank IDs
            bank_ids = {}
            for bank_name in df['bank'].unique():
                cursor.execute("SELECT bank_id FROM banks WHERE name = :name", [str(bank_name)])
                bank_ids[bank_name] = cursor.fetchone()[0]
                logging.info(f"Bank {bank_name} has ID {bank_ids[bank_name]}")
            
            # Insert reviews
            inserted_count = 0
            for i, row in df.iterrows():
                # Prepare data
                if isinstance(row['themes'], list):
                    themes = ','.join(row['themes'])
                else:
                    themes = str(row['themes'])
                
                try:
                    cursor.execute("""
                        INSERT INTO reviews (
                            bank_id, content, clean_content, rating, review_date,
                            source, sentiment, sentiment_score, themes
                        ) VALUES (
                            :bank_id, :content, :clean_content, :rating, TO_DATE(:review_date, 'YYYY-MM-DD'),
                            :source, :sentiment, :sentiment_score, :themes
                        )
                    """, {
                        'bank_id': bank_ids[row['bank']],
                        'content': str(row['review'])[:4000],
                        'clean_content': str(row['clean_review'])[:4000],
                        'rating': int(row['rating']),
                        'review_date': str(row['date']),
                        'source': str(row['source']),
                        'sentiment': str(row['sentiment']),
                        'sentiment_score': float(row['sentiment_score']),
                        'themes': themes[:500]
                    })
                    inserted_count += 1
                except Exception as e:
                    logging.warning(f"Skipping row {i} due to error: {str(e)}")
                
                # Commit every 100 records
                if inserted_count % 100 == 0:
                    connection.commit()
                    logging.info(f"Inserted {inserted_count} reviews")
            
            connection.commit()
            logging.info(f"Successfully inserted {inserted_count}/{len(df)} reviews")
            return True
            
    except Exception as e:
        logging.error(f"Python insertion failed: {str(e)}")
        connection.rollback()
        return False

def main():
    # Load analyzed data
    df = pd.read_csv("data/analyzed/reviews_with_themes.csv")
    
    # Convert themes to lists if they're strings
    if isinstance(df['themes'].iloc[0], str):
        try:
            df['themes'] = df['themes'].apply(eval)
        except:
            df['themes'] = df['themes'].apply(str)
    
    # Connect to Oracle
    try:
        # Create connection
        dsn = oracledb.makedsn("localhost", 1521, service_name="XEPDB1")
        connection = oracledb.connect(
            user="system",
            password="admin",
            dsn=dsn
        )
        logging.info("Connected to Oracle database")
        
        # Create tables
        create_tables(connection)
        
        # Insert banks (FIXED: pass value twice)
        with connection.cursor() as cursor:
            for bank_name in df['bank'].unique():
                try:
                    cursor.execute("""
                        INSERT INTO banks (name) 
                        SELECT :name FROM DUAL
                        WHERE NOT EXISTS (
                            SELECT 1 FROM banks WHERE name = :name
                        )
                    """, [str(bank_name), str(bank_name)])
                except Exception as e:
                    logging.warning(f"Bank insertion warning: {str(e)}")
            connection.commit()
            logging.info("Banks inserted/verified")
        
        # First try SQL*Loader
        sqlldr_success = False
        try:
            sqlldr_success = load_data_via_sqlldr(df)
        except Exception as e:
            logging.error(f"SQL*Loader failed: {str(e)}")
        
        # Fallback to Python insertion if SQL*Loader failed
        if not sqlldr_success:
            logging.warning("Falling back to pure Python insertion")
            insert_data_pure_python(connection, df)
        
        # Verify data
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM reviews")
            count = cursor.fetchone()[0]
            logging.info(f"Total reviews in database: {count}")
            
            cursor.execute("""
                SELECT b.name, COUNT(*) 
                FROM reviews r
                JOIN banks b ON r.bank_id = b.bank_id
                GROUP BY b.name
            """)
            logging.info("Bank-wise review counts:")
            for row in cursor:
                logging.info(f"{row[0]}: {row[1]}")
                
    except Exception as e:
        logging.error(f"Database operation failed: {str(e)}", exc_info=True)
    finally:
        # Clean up temporary files
        temp_files = ['oracle_load.csv', 'load.ctl', 'load.log', 'post_load.sql']
        for file in temp_files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    logging.info(f"Removed temporary file: {file}")
                except Exception as e:
                    logging.warning(f"Error removing {file}: {str(e)}")
        
        if 'connection' in locals() and connection:
            connection.close()
            logging.info("Database connection closed")

if __name__ == "__main__":
    main()