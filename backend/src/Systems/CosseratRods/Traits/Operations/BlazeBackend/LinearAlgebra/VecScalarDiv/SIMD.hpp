#pragma once

#include "Systems/CosseratRods/Traits/Operations/BlazeBackend/LinearAlgebra/KernelGenerators/VecScalar/SIMD.hpp"
//
#include "Systems/CosseratRods/Traits/Operations/BlazeBackend/LinearAlgebra/VecScalarDiv/BaseTemplate.hpp"
#include "Systems/CosseratRods/Traits/Operations/BlazeBackend/LinearAlgebra/VecScalarDiv/Operation.hpp"
//
#include "Systems/CosseratRods/Components/Noexcept.hpp"
//
#include "Utilities/ForceInline.hpp"
//
#include <utility>  // forward

namespace elastica {

  namespace cosserat_rod {

    template <>
    struct VecScalarDivOp<VecScalarDivKind::simd> {
      template <typename... Args>  // blaze Matrix expression type
      static ELASTICA_ALWAYS_INLINE auto apply(Args&&... args)
          COSSERATROD_LIB_NOEXCEPT->void {
        lazy_vector_scalar_kernel_simd(VectorScalarDivOperation{},
                                       std::forward<Args>(args)...);
      };
    };

  }  // namespace cosserat_rod

}  // namespace elastica