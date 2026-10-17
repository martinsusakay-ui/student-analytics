"""
spark_streaming.py - Baca dari Kafka (UnB + OULAD), tulis ke MongoDB
6 Kafka topic → 6 MongoDB collection
"""

import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, window, count,
    approx_count_distinct, lit, current_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, LongType, FloatType
)

# ============================================================
# KONFIGURASI
# ============================================================
CONFIG = {
    "kafka_bootstrap": "localhost:9092",
    "mongo_uri": "mongodb://admin:admin123@localhost:27017/?authSource=admin",
    "mongo_db": "moodle_analytics",
    "checkpoint_dir": "C:/Users/User/student-analytics/pipeline/checkpoints_v5",
    "trigger_interval": "30 seconds",
    "max_offsets_per_trigger": 2000,
}


# ============================================================
# SCHEMA UnB
# ============================================================
UNB_EVENTS_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("user_hash", StringType(), True),
    StructField("courseid", IntegerType(), True),
    StructField("component", StringType(), True),
    StructField("eventname", StringType(), True),
    StructField("action", StringType(), True),
    StructField("target", StringType(), True),
    StructField("timecreated", LongType(), True),
    StructField("event_time", StringType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])


# ============================================================
# SCHEMA OULAD
# ============================================================
OULAD_VLE_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("code_module", StringType(), True),
    StructField("code_presentation", StringType(), True),
    StructField("id_student", IntegerType(), True),
    StructField("id_site", IntegerType(), True),
    StructField("date", IntegerType(), True),
    StructField("sum_click", IntegerType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])

OULAD_ASSESSMENT_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("id_assessment", IntegerType(), True),
    StructField("id_student", IntegerType(), True),
    StructField("date_submitted", IntegerType(), True),
    StructField("is_banked", IntegerType(), True),
    StructField("score", FloatType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])

OULAD_STUDENTS_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("code_module", StringType(), True),
    StructField("code_presentation", StringType(), True),
    StructField("id_student", IntegerType(), True),
    StructField("gender", StringType(), True),
    StructField("region", StringType(), True),
    StructField("highest_education", StringType(), True),
    StructField("imd_band", StringType(), True),
    StructField("age_band", StringType(), True),
    StructField("num_of_prev_attempts", IntegerType(), True),
    StructField("studied_credits", IntegerType(), True),
    StructField("disability", StringType(), True),
    StructField("final_result", StringType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])

OULAD_COURSES_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("code_module", StringType(), True),
    StructField("code_presentation", StringType(), True),
    StructField("module_presentation_length", IntegerType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])

OULAD_REGISTRATION_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("code_module", StringType(), True),
    StructField("code_presentation", StringType(), True),
    StructField("id_student", IntegerType(), True),
    StructField("date_registration", IntegerType(), True),
    StructField("date_unregistration", IntegerType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])


# ============================================================
# SPARK SESSION
# ============================================================
def create_spark_session():
    spark = (
        SparkSession.builder
        .appName("MoodleStreamingAnalytics")
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1")
        .config("spark.sql.streaming.checkpointLocation", CONFIG["checkpoint_dir"])
        .config("spark.sql.shuffle.partitions", "6")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


# ============================================================
# WRITE TO MONGODB
# ============================================================
def write_to_mongodb(df, collection_name, checkpoint_name):
    """Tulis streaming DataFrame ke MongoDB via PyMongo."""
    
    def write_batch(batch_df, batch_id):
        try:
            count_val = batch_df.count()
            if count_val > 0:
                records = batch_df.toJSON().collect()
                docs = [json.loads(r) for r in records]
                
                from pymongo import MongoClient
                client = MongoClient(CONFIG["mongo_uri"])
                db = client[CONFIG["mongo_db"]]
                collection = db[collection_name]
                
                if docs:
                    collection.insert_many(docs, ordered=False)
                    print(f"[MONGO] Batch {batch_id}: {len(docs)} docs → {collection_name}")
                
                client.close()
        except Exception as e:
            print(f"[MONGO ERROR] {collection_name} batch {batch_id}: {e}")
    
    return (
        df.writeStream
        .foreachBatch(write_batch)
        .outputMode("append")
        .option("checkpointLocation", f"{CONFIG['checkpoint_dir']}/{checkpoint_name}")
        .trigger(processingTime=CONFIG["trigger_interval"])
        .start()
    )


# ============================================================
# PROCESS STREAM
# ============================================================
def process_stream(spark, topic, schema, collection, checkpoint):
    """Baca Kafka topic → parse JSON → tulis MongoDB."""
    kafka_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", CONFIG["kafka_bootstrap"])
        .option("subscribe", topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .option("maxOffsetsPerTrigger", CONFIG["max_offsets_per_trigger"])
        .load()
    )
    
    parsed_df = (
        kafka_df
        .selectExpr("CAST(value AS STRING) as json_str")
        .select(from_json(col("json_str"), schema).alias("data"))
        .select("data.*")
        .withColumn("processing_time", current_timestamp())
    )
    
    return write_to_mongodb(parsed_df, collection, checkpoint)


# ============================================================
# MAIN
# ============================================================
def run():
    print("=" * 70)
    print("  SPARK STREAMING - UnB + OULAD → MongoDB")
    print("=" * 70)
    print(f"  Kafka      : {CONFIG['kafka_bootstrap']}")
    print(f"  MongoDB    : {CONFIG['mongo_db']}")
    print(f"  Trigger    : {CONFIG['trigger_interval']}")
    print(f"  Checkpoint : {CONFIG['checkpoint_dir']}")
    print("=" * 70 + "\n")
    
    spark = create_spark_session()
    
    queries = []
    
    # ========================================================
    # UnB — events
    # ========================================================
    print("[SPARK] Setup moodle-events (UnB)...")
    q = process_stream(
        spark, "moodle-events", UNB_EVENTS_SCHEMA,
        "events", "unb_events"
    )
    queries.append(q)
    
    # ========================================================
    # OULAD — VLE
    # ========================================================
    print("[SPARK] Setup oulad-vle...")
    q = process_stream(
        spark, "oulad-vle", OULAD_VLE_SCHEMA,
        "oulad_vle", "oulad_vle"
    )
    queries.append(q)
    
    # ========================================================
    # OULAD — Assessment
    # ========================================================
    print("[SPARK] Setup oulad-assessment...")
    q = process_stream(
        spark, "oulad-assessment", OULAD_ASSESSMENT_SCHEMA,
        "oulad_assessment", "oulad_assessment"
    )
    queries.append(q)
    
    # ========================================================
    # OULAD — Students
    # ========================================================
    print("[SPARK] Setup oulad-students...")
    q = process_stream(
        spark, "oulad-students", OULAD_STUDENTS_SCHEMA,
        "oulad_students", "oulad_students"
    )
    queries.append(q)
    
    # ========================================================
    # OULAD — Courses
    # ========================================================
    print("[SPARK] Setup oulad-courses...")
    q = process_stream(
        spark, "oulad-courses", OULAD_COURSES_SCHEMA,
        "oulad_courses", "oulad_courses"
    )
    queries.append(q)
    
    # ========================================================
    # OULAD — Registration
    # ========================================================
    print("[SPARK] Setup oulad-registration...")
    q = process_stream(
        spark, "oulad-registration", OULAD_REGISTRATION_SCHEMA,
        "oulad_registration", "oulad_registration"
    )
    queries.append(q)
    
    print(f"\n{'='*70}")
    print(f"  {len(queries)} STREAM AKTIF")
    print(f"{'='*70}")
    print(f"  Tekan Ctrl+C untuk stop\n")
    
    # ========================================================
    # WAIT FOR TERMINATION
    # ========================================================
    try:
        spark.streams.awaitAnyTermination()
    except KeyboardInterrupt:
        print(f"\n[STOP] Dihentikan user")
    finally:
        for q in queries:
            try:
                q.stop()
            except:
                pass
        spark.stop()
        print(f"[DONE] Spark session dihentikan")


if __name__ == "__main__":
    run()