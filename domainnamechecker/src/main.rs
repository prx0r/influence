use anyhow::Result;
use chrono::Utc;
use clap::{Parser, Subcommand};
use hickory_proto::rr::RecordType;
use hickory_resolver::TokioAsyncResolver;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Parser)]
#[command(name = "domainnamechecker")]
#[command(about = "Domain Intelligence Engine — CLI for checking domain availability via DNS")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Check domain(s) for DNS records
    Check {
        /// Domain(s) to check
        #[arg(required = true)]
        domains: Vec<String>,

        /// Output format
        #[arg(short, long, default_value = "table")]
        format: OutputFormat,
    },
}

#[derive(Debug, Clone, clap::ValueEnum)]
enum OutputFormat {
    Table,
    Json,
}

#[derive(Serialize, Deserialize, Debug)]
struct DomainResult {
    domain: String,
    has_dns: bool,
    dns_records: HashMap<String, Vec<String>>,
    checked_at: String,
    verification_method: String,
    confidence: String,
    schema_version: String,
}

#[derive(Serialize, Deserialize, Debug)]
struct CheckResponse {
    results: Vec<DomainResult>,
    metadata: ResponseMetadata,
}

#[derive(Serialize, Deserialize, Debug)]
struct ResponseMetadata {
    total: usize,
    checked: usize,
    timestamp: String,
}

fn validate_domain(domain: &str) -> Result<(), String> {
    if domain.is_empty() || !domain.contains('.') {
        return Err(format!("'{}' is not a valid domain format", domain));
    }
    Ok(())
}

async fn check_domain(resolver: &TokioAsyncResolver, domain: &str) -> DomainResult {
    let mut dns_records: HashMap<String, Vec<String>> = HashMap::new();
    let mut has_dns = false;

    let record_types = [
        ("A", RecordType::A),
        ("AAAA", RecordType::AAAA),
        ("MX", RecordType::MX),
        ("NS", RecordType::NS),
        ("TXT", RecordType::TXT),
        ("CNAME", RecordType::CNAME),
    ];

    for (name, rtype) in &record_types {
        if let Ok(response) = resolver.lookup(domain, *rtype).await {
            let records: Vec<String> = response.iter().map(|r| r.to_string()).collect();
            if !records.is_empty() {
                has_dns = true;
                dns_records.insert(name.to_string(), records);
            }
        }
    }

    let confidence = if has_dns { "confirmed" } else { "unknown" };

    DomainResult {
        domain: domain.to_string(),
        has_dns,
        dns_records,
        checked_at: Utc::now().to_rfc3339(),
        verification_method: "dns_lookup".into(),
        confidence: confidence.into(),
        schema_version: "3.0.0".into(),
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Check { domains, format } => {
            let resolver = TokioAsyncResolver::tokio_from_system_conf()?;
            let mut results = Vec::new();

            for domain in &domains {
                if let Err(e) = validate_domain(domain) {
                    eprintln!("Error: {}", e);
                    continue;
                }
                let result = check_domain(&resolver, domain).await;
                results.push(result);
            }

            let response = CheckResponse {
                metadata: ResponseMetadata {
                    total: domains.len(),
                    checked: results.len(),
                    timestamp: Utc::now().to_rfc3339(),
                },
                results,
            };

            match format {
                OutputFormat::Json => {
                    println!("{}", serde_json::to_string_pretty(&response)?);
                }
                OutputFormat::Table => {
                    for result in &response.results {
                        println!("Checking: {}", result.domain);
                        if result.has_dns {
                            println!("  ✓ Has DNS records (confidence: {})", result.confidence);
                            for (record_type, records) in &result.dns_records {
                                println!("    {}: {:?}", record_type, records);
                            }
                        } else {
                            println!("  ✗ No DNS records found (POSSIBLE AVAILABLE)");
                        }
                    }
                    println!(
                        "\nChecked: {}/{}",
                        response.metadata.checked, response.metadata.total
                    );
                }
            }
        }
    }

    Ok(())
}
