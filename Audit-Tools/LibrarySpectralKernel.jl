#!/usr/bin/env julia
"""
Audit-Tools/LibrarySpectralKernel.jl
Stage 3: Computes the conceptual Graph Laplacian eigenspectrum (λ_1 ... λ_N),
isolated thematic silos, and Fiedler bridge manuscripts from `library_snapshot_manifest.json`.
"""

module LibrarySpectralKernel

using JSON
using LinearAlgebra

export audit_library_spectrum

function audit_library_spectrum(manifest_path::AbstractString)
    data = JSON.parsefile(manifest_path)
    docs = data["manuscripts"]
    raw_B = data["incidence_matrix"]

    N = length(docs)
    if N == 0
        error("No text manuscripts found in manifest.")
    end

    M = length(data["concept_tokens"])
    B = zeros(Float64, N, M)
    for i in 1:N
        row = raw_B[i]
        for j in 1:M
            B[i, j] = Float64(row[j])
        end
    end

    W = B * B'
    for i in 1:N
        W[i, i] = 0.0
    end
    degrees = vec(sum(W, dims=2))
    L = Diagonal(degrees) - W

    eig = eigen(Symmetric(L))
    vals = eig.values
    vecs = eig.vectors

    tol = 1e-9
    zero_count = count(v -> abs(v) <= tol, vals)
    pos_idx = findfirst(v -> v > tol, vals)
    lambda_pos = isnothing(pos_idx) ? 0.0 : vals[pos_idx]
    fiedler_vec = isnothing(pos_idx) ? zeros(Float64, N) : vecs[:, pos_idx]

    hubs = sort(
        [(docs[i]["path"], Int(round(degrees[i])), round(abs(fiedler_vec[i]), digits=6), docs[i]["indexed_in_index_md"]) for i in 1:N],
        by = x -> (-x[2], x[1]),
    )
    isolated = [docs[i]["path"] for i in 1:N if degrees[i] == 0.0]

    return Dict{String, Any}(
        "target_surface" => data["target_surface"],
        "manifest_sha256" => data["manifest_sha256"],
        "total_manuscripts" => N,
        "index_coverage_pq" => data["index_coverage_pq"],
        "orphan_binary_stems" => data["orphan_binary_stems"],
        "connected_components" => zero_count,
        "isolated_thematic_silos" => length(isolated),
        "first_nonzero_eigenvalue" => round(lambda_pos, digits=6),
        "spectral_radius_laplacian" => round(maximum(vals), digits=6),
        "top_conceptual_bridge_manuscripts" => [
            Dict("path" => p, "coupling_degree" => d, "fiedler_weight" => f, "in_index_md" => idx)
            for (p, d, f, idx) in hubs[1:min(12, N)]
        ],
        "sample_isolated_manuscripts" => isolated[1:min(15, length(isolated))],
    )
end

function main()
    manifest_path = joinpath(@__DIR__, "library_snapshot_manifest.json")
    out_path = joinpath(@__DIR__, "library_spectral_report.json")
    if !isfile(manifest_path)
        error("Missing $manifest_path — run `python3 library_ingest.py` first.")
    end

    report = audit_library_spectrum(manifest_path)
    open(out_path, "w") do io
        JSON.print(io, report, 2)
    end

    println("=== library-Specimen SPECTRAL & PROVENANCE AUDIT COMPLETE ===")
    println("Manuscripts Audited      : ", report["total_manuscripts"])
    println("INDEX.md Coverage (p/q)  : ", report["index_coverage_pq"])
    println("Orphan Binary Stems      : ", length(report["orphan_binary_stems"]))
    println("Disconnected Components  : ", report["connected_components"])
    println("First Non-Zero λ (Core)  : ", report["first_nonzero_eigenvalue"])
    println("Saved report to          : ", out_path)
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end

end # module
